"""Redis-Optimized Agent Example.

Demonstrates how to build an agent that leverages Redis features
for coordination, heartbeats, and messaging.

Run with: python examples/redis_optimized_agent.py

Prerequisites:
    Configure Redis via .env file:
        REDIS_ENABLED=true
        REDIS_MODE=cloud        # or "local" for localhost
        REDIS_HOST=your-host
        REDIS_PORT=your-port
        REDIS_PASSWORD=your-password
"""

import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Load .env from project root
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import redis

# DEPRECATED: Use attune_redis.config.RedisPluginConfig for new code.
# This import will break in v4.0.0.
from attune.redis_config import get_redis_config


def _get_redis_kwargs() -> dict:
    """Get Redis connection kwargs from environment configuration."""
    config = get_redis_config()
    kwargs = config.to_redis_kwargs()
    kwargs["decode_responses"] = True
    return kwargs


@dataclass
class Task:
    id: str
    name: str


class RedisOptimizedAgent:
    """An agent that uses Redis for coordination and state management."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.redis = redis.Redis(**_get_redis_kwargs())

        # Verify connection
        self.redis.ping()
        print(f"✅ Agent '{agent_id}' connected to Redis")

        # Register agent heartbeat
        self._start_heartbeat()

    def _start_heartbeat(self):
        """Register agent as alive in Redis."""
        key = f"agent:heartbeat:{self.agent_id}"
        self.redis.hset(
            key,
            mapping={
                "agent_id": self.agent_id,
                "status": "starting",
                "started_at": time.time(),
                "last_beat": time.time(),
            },
        )
        self.redis.expire(key, 60)  # TTL: 60 seconds
        print(f"💓 Heartbeat registered for '{self.agent_id}'")

    def beat(self, status: str = "running", current_task: str = ""):
        """Update heartbeat with current status."""
        key = f"agent:heartbeat:{self.agent_id}"
        self.redis.hset(
            key,
            mapping={
                "status": status,
                "current_task": current_task,
                "last_beat": time.time(),
            },
        )
        self.redis.expire(key, 60)  # Refresh TTL
        print(f"💓 Beat: {status} - {current_task}")

    def signal(self, signal_type: str, target_agent: str, payload: dict):
        """Send a coordination signal to another agent."""
        import json

        signal_key = f"signal:{target_agent}:{int(time.time() * 1000)}"
        signal_data = {
            "type": signal_type,
            "source": self.agent_id,
            "target": target_agent,
            "payload": json.dumps(payload),
            "timestamp": time.time(),
        }
        self.redis.hset(signal_key, mapping=signal_data)
        self.redis.expire(signal_key, 300)  # 5 minute TTL

        # Also publish to Pub/Sub for real-time delivery
        self.redis.publish(f"signals:{target_agent}", json.dumps(signal_data))
        print(f"📡 Signal sent: {signal_type} → {target_agent}")

    def process(self, task: Task):
        """Process a task with Redis coordination."""
        print(f"\n🔄 Processing task: {task.name}")

        # Update heartbeat
        self.beat(status="running", current_task=task.name)

        # Simulate work
        for i in range(3):
            time.sleep(0.5)
            progress = (i + 1) / 3
            self.beat(status="running", current_task=f"{task.name} ({progress:.0%})")

        # Signal completion
        self.signal(
            signal_type="task_complete",
            target_agent="coordinator",
            payload={"task_id": task.id, "result": "success"},
        )

        self.beat(status="idle", current_task="")
        print(f"✅ Task complete: {task.name}")

    def get_active_agents(self) -> list[str]:
        """Find all agents with active heartbeats."""
        pattern = "agent:heartbeat:*"
        agents = []
        for key in self.redis.scan_iter(pattern):
            data = self.redis.hgetall(key)
            if data:
                last_beat = float(data.get("last_beat", 0))
                if time.time() - last_beat < 60:  # Active in last 60s
                    agents.append(data.get("agent_id", "unknown"))
        return agents

    def shutdown(self):
        """Clean shutdown with status update."""
        self.beat(status="shutdown", current_task="")
        print(f"👋 Agent '{self.agent_id}' shutting down")


def main():
    print("=" * 60)
    print("REDIS-OPTIMIZED AGENT DEMO")
    print("=" * 60)

    # Create agent
    agent = RedisOptimizedAgent(agent_id="healthcare-processor-1")

    # Check for other active agents
    active = agent.get_active_agents()
    print(f"\n📊 Active agents: {active}")

    # Process some tasks
    tasks = [
        Task(id="T001", name="Drug Interaction Check"),
        Task(id="T002", name="Clinical Alert Processing"),
        Task(id="T003", name="Patient Risk Score"),
    ]

    for task in tasks:
        agent.process(task)

    # Shutdown
    agent.shutdown()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
