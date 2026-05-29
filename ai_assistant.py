"""AI-powered assistant for guiding users through upgrades."""

import os
import json
from typing import Optional, List, Dict
from anthropic import Anthropic
from dotenv import load_dotenv

from system_detector import SystemDetector
from upgrade_paths import UpgradePathFinder
from compatibility_checker import CompatibilityChecker
from backup_advisor import BackupAdvisor


class UpgradeAssistant:
    """AI assistant that guides users through the upgrade process."""

    def __init__(self, api_key: Optional[str] = None):
        load_dotenv()
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Set it in .env file or environment variable."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.conversation_history: List[Dict] = []
        self.system_context = None
        self._initialize_system_context()

    def _initialize_system_context(self):
        """Gather system information for AI context."""
        try:
            system = SystemDetector.detect()
            prereqs = SystemDetector.check_prerequisites()
            paths = UpgradePathFinder.find_paths(system)
            recommended_path = UpgradePathFinder.recommend_best_path(paths)

            checker = CompatibilityChecker(system)
            checks = checker.run_all_checks()

            critical_issues = [c for c in checks if c.severity == 'critical' and not c.passed]
            warnings = [c for c in checks if c.severity == 'warning' and not c.passed]

            backup_recs = BackupAdvisor.get_recommendations(system)

            self.system_context = {
                'system': {
                    'os': str(system),
                    'os_id': system.os_id,
                    'version': system.os_version,
                    'is_rhel': system.is_rhel_based,
                    'is_fedora': system.is_fedora,
                    'architecture': system.architecture,
                    'kernel': system.kernel,
                },
                'prerequisites': prereqs,
                'upgrade_path': {
                    'available': recommended_path is not None,
                    'from': recommended_path.from_version if recommended_path else None,
                    'to': recommended_path.to_version if recommended_path else None,
                    'method': recommended_path.method if recommended_path else None,
                    'risk': recommended_path.risk_level if recommended_path else None,
                    'notes': recommended_path.notes if recommended_path else [],
                } if recommended_path else None,
                'compatibility': {
                    'critical_issues': len(critical_issues),
                    'warnings': len(warnings),
                    'issues': [
                        {
                            'name': c.name,
                            'message': c.message,
                            'remediation': c.remediation
                        } for c in critical_issues + warnings
                    ]
                },
                'backups': {
                    'critical_count': len([b for b in backup_recs if b.priority == 'critical']),
                    'recommended_count': len([b for b in backup_recs if b.priority == 'recommended']),
                }
            }
        except Exception as e:
            self.system_context = {'error': f'Could not gather system info: {str(e)}'}

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current system context."""
        return f"""You are an expert Linux system administrator assistant helping users upgrade their systems safely.

Your role is to:
1. Guide users through the upgrade process step-by-step
2. Explain technical concepts in clear, accessible language
3. Warn about risks and recommend best practices
4. Answer questions about their specific system and upgrade path
5. Help troubleshoot issues that arise

Current System Context:
{json.dumps(self.system_context, indent=2)}

Guidelines:
- Be conversational and supportive, not just technical
- Always prioritize data safety and backups
- Explain the "why" behind recommendations
- If the user seems uncertain, ask clarifying questions
- Offer to perform actions (checking logs, running commands) when appropriate
- Use analogies when explaining complex concepts
- Be honest about risks and don't downplay potential issues

When discussing upgrades:
- RHEL/CentOS upgrades use Leapp (in-place upgrade tool)
- Fedora upgrades use DNF system-upgrade plugin (managed via Ansible)
- Always recommend backups before any upgrade
- Explain what will happen during the upgrade process
- Set realistic expectations about downtime and complexity

Remember: You're a helpful guide, not just a command executor. Build trust and ensure the user feels confident."""

    def chat(self, user_message: str) -> str:
        """Send a message and get AI response."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=self._build_system_prompt(),
                messages=self.conversation_history
            )

            assistant_message = response.content[0].text

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return assistant_message

        except Exception as e:
            return f"Error communicating with AI assistant: {str(e)}"

    def start_guided_session(self) -> str:
        """Start an interactive guided upgrade session."""
        greeting = self.chat(
            "Hello! I need help understanding my system and upgrading it safely. "
            "Can you guide me through the process?"
        )
        return greeting

    def get_context_summary(self) -> Dict:
        """Get a summary of the current system context."""
        return self.system_context

    def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []

    def export_conversation(self, filepath: str):
        """Export conversation history to a file."""
        with open(filepath, 'w') as f:
            json.dump({
                'system_context': self.system_context,
                'conversation': self.conversation_history
            }, f, indent=2)
