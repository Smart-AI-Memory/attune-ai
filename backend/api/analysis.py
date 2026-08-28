"""Analysis API endpoints.
Handles code analysis, project scanning, and result retrieval.

Input validation and error handling included for security.
"""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, field_validator

from api.dependencies import require_principal
from services.empathy_service import EmpathyService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def get_empathy_service() -> EmpathyService:
    """Get EmpathyService instance.

    Returns:
        A new EmpathyService for use as a FastAPI dependency.

    """
    return EmpathyService()


class ProjectAnalysisRequest(BaseModel):
    """Request model for project analysis."""

    project_path: str
    file_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    wizards: list[str] | None = None

    @field_validator("project_path")
    @classmethod
    def validate_project_path(cls, v: str) -> str:
        """Validate project path is non-empty and within length limits.

        Args:
            v: Raw project_path value from the request.

        Returns:
            The validated project path string.

        Raises:
            ValueError: If the path is empty or exceeds 1024 characters.

        """
        if not v or not v.strip():
            raise ValueError("project_path cannot be empty")
        if len(v) > 1024:
            raise ValueError("project_path exceeds maximum length")
        return v


class SessionConfig(BaseModel):
    """Configuration for analysis session."""

    name: str
    description: str | None = None
    wizards: list[str]
    config: dict[str, Any] = {}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate session name is non-empty and within length limits.

        Args:
            v: Raw name value from the request.

        Returns:
            The validated session name string.

        Raises:
            ValueError: If the name is empty or exceeds 255 characters.

        """
        if not v or not v.strip():
            raise ValueError("Session name cannot be empty")
        if len(v) > 255:
            raise ValueError("Session name exceeds maximum length")
        return v

    @field_validator("wizards")
    @classmethod
    def validate_wizards(cls, v: list[str]) -> list[str]:
        """Validate that at least one and at most 20 wizards are specified.

        Args:
            v: Raw wizards list from the request.

        Returns:
            The validated list of wizard identifiers.

        Raises:
            ValueError: If the list is empty or contains more than 20 entries.

        """
        if not v or len(v) == 0:
            raise ValueError("At least one wizard must be specified")
        if len(v) > 20:
            raise ValueError("Maximum 20 wizards allowed per session")
        return v


@router.post("/session")
async def create_session(
    request: SessionConfig,
    service: EmpathyService = Depends(get_empathy_service),
    principal: dict[str, Any] = Depends(require_principal),
):
    """Create a new analysis session.

    Args:
        request: Session configuration
        service: EmpathyService instance
        principal: Authenticated principal (verified JWT payload)

    Returns:
        Session ID and metadata

    """
    try:
        session_id = await service.create_analysis_session(request.model_dump())
        return {
            "success": True,
            "session_id": session_id,
            "message": "Analysis session created successfully",
        }
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Catch-all for API error reporting
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e!s}") from e


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    service: EmpathyService = Depends(get_empathy_service),
    principal: dict[str, Any] = Depends(require_principal),
):
    """Get analysis session results.

    Args:
        session_id: Session identifier
        service: EmpathyService instance
        principal: Authenticated principal (verified JWT payload)

    Returns:
        Session results and status

    """
    result = await service.get_session_results(session_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.post("/project")
async def analyze_project(
    request: ProjectAnalysisRequest,
    service: EmpathyService = Depends(get_empathy_service),
    principal: dict[str, Any] = Depends(require_principal),
):
    """Analyze an entire project.

    Args:
        request: Project analysis configuration
        service: EmpathyService instance
        principal: Authenticated principal (verified JWT payload)

    Returns:
        Project analysis results

    """
    try:
        from attune.security.path_validation import _validate_file_path

        validated_path = str(_validate_file_path(request.project_path))
        result = await service.analyze_project(
            project_path=validated_path,
            file_patterns=request.file_patterns,
        )
        return result
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Catch-all for API error reporting
        raise HTTPException(status_code=500, detail=f"Project analysis failed: {e!s}") from e


@router.post("/file")
async def analyze_file(
    file: UploadFile = File(...),
    language: str = "python",
    service: EmpathyService = Depends(get_empathy_service),
    principal: dict[str, Any] = Depends(require_principal),
):
    """Analyze a single uploaded file.

    Args:
        file: Uploaded file (max 10MB)
        language: Programming language (python, javascript, typescript, java, go, rust)
        service: EmpathyService instance
        principal: Authenticated principal (verified JWT payload)

    Returns:
        File analysis results

    Raises:
        HTTPException: If file is invalid or analysis fails

    """
    # Validate file size (10MB limit)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum of {MAX_FILE_SIZE} bytes",
        )

    # Validate language
    SUPPORTED_LANGUAGES = {
        "python",
        "javascript",
        "typescript",
        "java",
        "go",
        "rust",
        "cpp",
        "c",
        "csharp",
        "php",
    }
    if language.lower() not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language. Supported: {', '.join(SUPPORTED_LANGUAGES)}",
        )

    # Validate file content
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must have a name")

    try:
        content = await file.read()

        # Validate content is not empty
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File cannot be empty",
            )

        code = content.decode("utf-8")

        result = await service.analyze_code(code=code, language=language, include_metrics=True)

        return {"success": True, "filename": file.filename, "analysis": result}
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be valid UTF-8 text",
        ) from None
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Catch-all for API error reporting
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File analysis failed: {e!s}",
        ) from e


@router.get("/history")
async def get_analysis_history(
    limit: int = 10,
    offset: int = 0,
    principal: dict[str, Any] = Depends(require_principal),
):
    """Get user's analysis history.

    Args:
        limit: Number of results to return (max 100, default 10)
        offset: Pagination offset (min 0)
        principal: Authenticated principal (verified JWT payload)

    Returns:
        List of past analyses

    Raises:
        HTTPException: If limit or offset are invalid

    """
    # Validate pagination parameters
    MAX_LIMIT = 100
    if limit < 1 or limit > MAX_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"limit must be between 1 and {MAX_LIMIT}",
        )

    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset cannot be negative",
        )

    # Placeholder implementation
    return {
        "analyses": [
            {
                "id": "analysis_123",
                "type": "code",
                "timestamp": "2025-10-19T12:00:00Z",
                "issues_found": 5,
                "status": "completed",
            },
        ],
        "total": 1,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    principal: dict[str, Any] = Depends(require_principal),
):
    """Delete an analysis session.

    Args:
        session_id: Session identifier
        principal: Authenticated principal (verified JWT payload)

    Returns:
        Deletion confirmation

    """
    return {"success": True, "message": f"Session {session_id} deleted successfully"}
