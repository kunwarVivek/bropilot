#!/usr/bin/env python3
"""
Error Recovery System Demonstration.

This script demonstrates the advanced error recovery capabilities
of the execution layer, showing how different types of errors
are classified, handled, and recovered from automatically.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.exceptions import TaskExecutionError, BrowserError, TimeoutError, ConfigurationError
from src.execution.error_recovery import (
    ExecutionErrorRecovery, RecoveryContext, RecoveryPriority,
    ExecutionErrorCategory
)
from src.infrastructure.logging.logger import StructuredLogger


class ErrorRecoveryDemo:
    """Demonstration of the error recovery system."""
    
    def __init__(self):
        """Initialize the demo."""
        self.logger = StructuredLogger("error_recovery_demo")
        self.recovery_system = ExecutionErrorRecovery(
            llm_provider=None,  # No LLM for demo
            enable_learning=True,
            max_recovery_attempts=3
        )
        
        self.demo_scenarios = [
            {
                "name": "Adapter Failure",
                "error": TaskExecutionError("Adapter connection lost"),
                "context": RecoveryContext(
                    task_id="demo_task_1",
                    adapter_id="demo_adapter",
                    priority=RecoveryPriority.IMMEDIATE
                ),
                "description": "Simulates an adapter connection failure with immediate recovery"
            },
            {
                "name": "Browser Crash",
                "error": BrowserError("Browser process crashed unexpectedly"),
                "context": RecoveryContext(
                    task_id="demo_task_2",
                    browser_session_id="demo_session",
                    priority=RecoveryPriority.URGENT
                ),
                "description": "Simulates a browser crash requiring urgent recovery"
            },
            {
                "name": "Task Timeout",
                "error": TimeoutError("Operation timed out after 30 seconds"),
                "context": RecoveryContext(
                    task_id="demo_task_3",
                    timeout_seconds=30.0,
                    priority=RecoveryPriority.NORMAL
                ),
                "description": "Simulates a task timeout with normal priority recovery"
            },
            {
                "name": "Configuration Error",
                "error": ConfigurationError("Invalid configuration parameter"),
                "context": RecoveryContext(
                    task_id="demo_task_4",
                    priority=RecoveryPriority.NORMAL
                ),
                "description": "Simulates a configuration error requiring validation and fix"
            },
            {
                "name": "Resource Exhaustion",
                "error": Exception("Memory limit exceeded"),
                "context": RecoveryContext(
                    task_id="demo_task_5",
                    priority=RecoveryPriority.BACKGROUND
                ),
                "description": "Simulates resource exhaustion requiring cleanup"
            }
        ]
    
    async def run_demo(self) -> None:
        """Run the complete error recovery demonstration."""
        print("🔧 Error Recovery System Demonstration")
        print("=" * 60)
        print()
        
        # Start background recovery processor
        await self.recovery_system.start_background_recovery()
        
        try:
            print("🚀 Starting error recovery demonstrations...")
            print()
            
            # Run each demo scenario
            for i, scenario in enumerate(self.demo_scenarios, 1):
                await self._run_scenario(i, scenario)
                print()
                
                # Brief pause between scenarios
                await asyncio.sleep(1.0)
            
            # Show analytics and metrics
            await self._show_analytics()
            
            # Generate and show recovery report
            await self._show_recovery_report()
            
        finally:
            # Stop background processor
            await self.recovery_system.stop_background_recovery()
        
        print("✅ Error recovery demonstration completed!")
    
    async def _run_scenario(self, scenario_num: int, scenario: Dict[str, Any]) -> None:
        """Run a single error recovery scenario."""
        print(f"📋 Scenario {scenario_num}: {scenario['name']}")
        print(f"   Description: {scenario['description']}")
        print(f"   Error Type: {type(scenario['error']).__name__}")
        print(f"   Priority: {scenario['context'].priority.value}")
        
        start_time = time.time()
        
        try:
            # Handle the error
            recovery_result = await self.recovery_system.handle_execution_error(
                scenario['error'],
                scenario['context'],
                f"demo_correlation_{scenario_num}"
            )
            
            execution_time = time.time() - start_time
            
            # Show results
            if recovery_result.get("success"):
                print(f"   ✅ Recovery: SUCCESS")
                if "strategy_used" in recovery_result:
                    print(f"   🔧 Strategy: {recovery_result['strategy_used']}")
            elif recovery_result.get("queued_for_background"):
                print(f"   ⏳ Recovery: QUEUED for background processing")
                print(f"   ⏱️  Estimated time: {recovery_result.get('estimated_recovery_time', 'unknown')}s")
            else:
                print(f"   ❌ Recovery: FAILED")
            
            print(f"   ⏱️  Execution time: {execution_time:.3f}s")
            
            # Show error classification
            error_category = self.recovery_system._classify_execution_error(
                scenario['error'], scenario['context']
            )
            print(f"   🏷️  Classified as: {error_category}")
            
        except Exception as e:
            print(f"   ❌ Demo scenario failed: {e}")
    
    async def _show_analytics(self) -> None:
        """Show error analytics and metrics."""
        print("📊 Error Recovery Analytics")
        print("-" * 40)
        
        # Get metrics
        metrics = self.recovery_system.get_recovery_metrics()
        analytics = self.recovery_system.get_error_analytics()
        
        print(f"Total Errors Handled: {metrics['total_errors']}")
        print(f"Total Recoveries: {metrics['total_recoveries']}")
        print(f"Recovery Success Rate: {metrics['recovery_success_rate']:.1%}")
        print(f"Average Recovery Time: {metrics['average_recovery_time']:.3f}s")
        print()
        
        print("Errors by Category:")
        for category, count in metrics['errors_by_category'].items():
            print(f"  • {category}: {count}")
        print()
        
        print("Recovery Strategies Used:")
        for strategy, count in metrics['recovery_strategies_used'].items():
            print(f"  • {strategy}: {count}")
        print()
        
        if analytics.get("total_errors_analyzed", 0) > 0:
            print("Success Rates by Category:")
            for category, rate in analytics.get("recovery_success_rates", {}).items():
                print(f"  • {category}: {rate:.1%}")
            print()
    
    async def _show_recovery_report(self) -> None:
        """Show comprehensive recovery report."""
        print("📋 Recovery Report Summary")
        print("-" * 40)
        
        try:
            report = await self.recovery_system.generate_recovery_report()
            
            # System health
            health = report["system_health"]
            print(f"System Operational: {'✅' if health['recovery_system_operational'] else '❌'}")
            print(f"Background Processor: {'✅' if health['background_processor_active'] else '❌'}")
            print(f"Learning Enabled: {'✅' if health['learning_enabled'] else '❌'}")
            print(f"Queue Backlog: {health['queue_backlog']} items")
            print()
            
            # Recommendations
            recommendations = report.get("recommendations", [])
            if recommendations:
                print("🔍 Recommendations:")
                for rec in recommendations[:3]:  # Show top 3
                    print(f"  • {rec['type'].title()}: {rec['recommendation']}")
                    print(f"    Priority: {rec['priority']}, Impact: {rec['impact']}")
                print()
            else:
                print("🎉 No recommendations - system performing optimally!")
                print()
            
            # Pattern analysis
            patterns = report.get("pattern_analysis", {})
            if patterns.get("problematic_patterns"):
                print("⚠️  Problematic Patterns Detected:")
                for pattern in patterns["problematic_patterns"][:2]:  # Show top 2
                    print(f"  • {pattern['pattern']}: {pattern['occurrences']} occurrences")
                    print(f"    Success rate: {pattern['success_rate']:.1%}")
                print()
            
        except Exception as e:
            print(f"❌ Failed to generate recovery report: {e}")
            print()


async def main():
    """Main function to run the error recovery demo."""
    demo = ErrorRecoveryDemo()
    
    try:
        await demo.run_demo()
        return 0
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
