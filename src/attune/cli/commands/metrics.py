"""Metrics commands for user statistics.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import sys

from attune.logging_config import get_logger
from attune.metrics.collector import MetricsCollector
from attune.persistence import StateManager

logger = get_logger(__name__)


def cmd_metrics_show(args):
    """Display metrics for a user.

    Args:
        args: Namespace object from argparse with attributes:
            - user (str): User ID to retrieve metrics for.
            - db (str): Path to metrics database (default: ./metrics.db).

    Returns:
        None: Prints user metrics to stdout. Exits with code 1 on failure.
    """
    db_path = args.db
    user_id = args.user

    logger.info(f"Retrieving metrics for user: {user_id} from {db_path}")

    collector = MetricsCollector(db_path)

    try:
        stats = collector.get_user_stats(user_id)

        logger.info(f"Successfully retrieved metrics for user: {user_id}")
        logger.info(f"=== Metrics for User: {user_id} ===\n")
        logger.info(f"Total Operations: {stats['total_operations']}")
        logger.info(f"Success Rate: {stats['success_rate']:.1%}")
        logger.info(f"Average Response Time: {stats.get('avg_response_time_ms', 0):.0f} ms")
        logger.info(f"\nFirst Use: {stats['first_use']}")
        logger.info(f"Last Use: {stats['last_use']}")

        logger.info("\nLevel Usage:")
        logger.info(f"  Level 1: {stats.get('level_1_count', 0)} uses")
        logger.info(f"  Level 2: {stats.get('level_2_count', 0)} uses")
        logger.info(f"  Level 3: {stats.get('level_3_count', 0)} uses")
        logger.info(f"  Level 4: {stats.get('level_4_count', 0)} uses")
        logger.info(f"  Level 5: {stats.get('level_5_count', 0)} uses")
    except (OSError, FileNotFoundError) as e:
        # Database file not found
        logger.error(f"Metrics database error: {e}")
        logger.error(f"✗ Cannot read metrics database: {e}")
        sys.exit(1)
    except KeyError as e:
        # User not found in database
        logger.error(f"User not found in metrics: {e}")
        logger.error(f"✗ User {user_id} not found: {e}")
        sys.exit(1)
    except Exception as e:
        # Unexpected errors retrieving metrics
        logger.exception(f"Unexpected error retrieving metrics for user {user_id}: {e}")
        logger.error(f"✗ Failed to retrieve metrics: {e}")
        sys.exit(1)


def cmd_state_list(args):
    """List saved user states.

    Args:
        args: Namespace object from argparse with attributes:
            - state_dir (str): Directory containing state files.

    Returns:
        None: Prints list of users with saved states.
    """
    state_dir = args.state_dir

    logger.info(f"Listing saved user states from: {state_dir}")

    manager = StateManager(state_dir)
    users = manager.list_users()

    logger.info(f"Found {len(users)} saved user states")
    logger.info(f"=== Saved User States: {state_dir} ===\n")
    logger.info(f"Total users: {len(users)}")

    if users:
        logger.info("\nUsers:")
        for user_id in users:
            logger.info(f"  - {user_id}")
