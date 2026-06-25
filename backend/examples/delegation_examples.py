# NOTICE: This file is protected under RCF-PL
"""
Example: Research Team with Agent Delegation

This example shows how to create a research coordinator that delegates
to specialized agents for different aspects of research.
"""

import asyncio
from app.services.delegation import (
    delegate_to_agent,
    delegate_parallel,
    delegate_sequential,
    format_delegation_summary
)


# [RCF:PROTECTED]
async def example_research_coordinator(user_id: int, db):
    """
    Research Coordinator Agent that delegates to specialists.

    User asks: "Research our competitor XYZ Corp"

    Coordinator breaks this into:
    1. Web research (parallel)
    2. Social media analysis (parallel)
    3. Pricing analysis (parallel)
    4. Report compilation (sequential after 1-3)
    """

    print("🔍 Research Coordinator starting...")

    # Phase 1: Parallel research
    parallel_tasks = [
        {
            "target_agent_id": "web_researcher",
            "task": "Find XYZ Corp's website, products, and recent news articles",
            "context": {"company": "XYZ Corp"}
        },
        {
            "target_agent_id": "social_analyzer",
            "task": "Analyze XYZ Corp's social media presence and engagement",
            "context": {"platforms": ["twitter", "linkedin"]}
        },
        {
            "target_agent_id": "price_tracker",
            "task": "Find XYZ Corp's pricing information and compare to ours",
            "context": {"our_pricing": "available_in_crm"}
        }
    ]

    print(f"  Delegating {len(parallel_tasks)} research tasks in parallel...")
    research_results = await delegate_parallel(
        parent_agent_id="research_coordinator",
        delegations=parallel_tasks,
        user_id=user_id,
        db=db
    )

    # Phase 2: Compile report (sequential)
    print("  Compiling research report...")
    report_result = await delegate_to_agent(
        parent_agent_id="research_coordinator",
        target_agent_id="report_writer",
        task="Create an executive summary of the research findings",
        context={
            "research_findings": [
                {
                    "source": r.agent_name,
                    "findings": r.response
                }
                for r in research_results
            ]
        },
        user_id=user_id,
        db=db
    )

    print("\n📊 Research Complete!")
    print(format_delegation_summary(research_results + [report_result]))

    return report_result.response


# [RCF:PROTECTED]
async def example_content_pipeline(user_id: int, db):
    """
    Content Pipeline: Research → Outline → Draft → Edit → SEO

    Each agent gets the output of the previous one.
    """

    print("✍️  Content Pipeline starting...")

    pipeline = [
        {
            "target_agent_id": "researcher",
            "task": "Research current AI trends and latest developments"
        },
        {
            "target_agent_id": "outline_writer",
            "task": "Create a blog post outline based on the research"
        },
        {
            "target_agent_id": "draft_writer",
            "task": "Write a 1000-word blog post following the outline"
        },
        {
            "target_agent_id": "editor",
            "task": "Edit and polish the draft for clarity and engagement"
        },
        {
            "target_agent_id": "seo_optimizer",
            "task": "Optimize the post for SEO and add meta description"
        }
    ]

    print(f"  Running {len(pipeline)}-stage pipeline...")
    results = await delegate_sequential(
        parent_agent_id="content_manager",
        delegations=pipeline,
        user_id=user_id,
        db=db,
        pass_context=True  # Each agent gets previous results
    )

    print("\n📝 Content Pipeline Complete!")

    # Final output is from last agent (SEO optimizer)
    final_content = results[-1].response

    print(f"\nStages completed: {len([r for r in results if r.success])}/{len(results)}")
    print(f"Final content length: {len(final_content)} characters")

    return final_content


# [RCF:PROTECTED]
async def example_customer_onboarding(user_id: int, db, customer_email: str):
    """
    Customer Onboarding: Multiple parallel actions.

    When a new customer signs up:
    1. Send welcome email
    2. Create CRM contact
    3. Schedule kickoff call
    4. Notify team in Slack
    """

    print(f"🎉 Onboarding new customer: {customer_email}")

    onboarding_tasks = [
        {
            "target_agent_id": "email_agent",
            "task": f"Send personalized welcome email to {customer_email}",
            "context": {
                "template": "welcome",
                "customer_email": customer_email
            }
        },
        {
            "target_agent_id": "crm_agent",
            "task": f"Create contact for {customer_email} and set up onboarding deal",
            "context": {
                "deal_value": 5000,
                "deal_stage": "onboarding"
            }
        },
        {
            "target_agent_id": "calendar_agent",
            "task": f"Schedule 30-min kickoff call with {customer_email} for next week",
            "context": {
                "duration_minutes": 30,
                "meeting_type": "kickoff"
            }
        },
        {
            "target_agent_id": "slack_agent",
            "task": f"Notify #sales channel: New customer {customer_email} onboarded",
            "context": {
                "channel": "#sales",
                "mention_team": True
            }
        }
    ]

    print(f"  Running {len(onboarding_tasks)} onboarding tasks...")
    results = await delegate_parallel(
        parent_agent_id="onboarding_coordinator",
        delegations=onboarding_tasks,
        user_id=user_id,
        db=db
    )

    # Check for failures
    failures = [r for r in results if not r.success]
    if failures:
        print(f"\n⚠️  {len(failures)} task(s) failed:")
        for f in failures:
            print(f"  - {f.agent_name}: {f.error}")
    else:
        print(f"\n✅ All {len(results)} onboarding tasks completed successfully!")

    return results


# [RCF:PROTECTED]
async def example_hierarchical_delegation(user_id: int, db):
    """
    Hierarchical: CEO → Managers → Workers

    CEO agent delegates to department managers,
    who then delegate to their team workers.
    """

    print("🏢 Hierarchical Organization starting...")

    # CEO delegates to department managers
    manager_tasks = [
        {
            "target_agent_id": "sales_manager",
            "task": "Get Q4 sales report from your team"
        },
        {
            "target_agent_id": "marketing_manager",
            "task": "Get Q4 marketing metrics from your team"
        }
    ]

    print("  CEO → Department Managers...")
    manager_results = await delegate_parallel(
        parent_agent_id="ceo_agent",
        delegations=manager_tasks,
        user_id=user_id,
        db=db
    )

    # Note: Each manager agent would internally delegate to their team
    # This requires managers to have delegation tools enabled

    print("\n📈 Executive Summary Ready!")
    print(format_delegation_summary(manager_results))

    return manager_results


# [RCF:PROTECTED]
async def example_error_recovery(user_id: int, db):
    """
    Error Recovery: Retry failed delegations.
    """

    print("🔄 Testing error recovery...")

    tasks = [
        {"target_agent_id": "agent1", "task": "Task 1"},
        {"target_agent_id": "nonexistent_agent", "task": "Task 2"},  # Will fail
        {"target_agent_id": "agent3", "task": "Task 3"},
    ]

    results = await delegate_parallel(
        parent_agent_id="coordinator",
        delegations=tasks,
        user_id=user_id,
        db=db
    )

    # Find failures
    failed = [r for r in results if not r.success]

    if failed:
        print(f"\n⚠️  {len(failed)} task(s) failed, retrying...")

        # Retry with fallback agents
        retry_tasks = [
            {
                "target_agent_id": "fallback_agent",
                "task": r.metadata.get("original_task", "Unknown task")
            }
            for r in failed
        ]

        retry_results = await delegate_parallel(
            parent_agent_id="coordinator",
            delegations=retry_tasks,
            user_id=user_id,
            db=db
        )

        print(f"  Retry complete: {len([r for r in retry_results if r.success])} succeeded")


# CLI command to test delegation
# [RCF:PROTECTED]
async def main():
    """Run delegation examples."""
    from app.database import get_db

    user_id = 1  # Example user

    async with get_db() as db:
        print("=" * 60)
        print("Agent Delegation Examples")
        print("=" * 60)

        # Example 1: Research Team
        print("\n\n1️⃣  Research Team Example")
        print("-" * 60)
        await example_research_coordinator(user_id, db)

        # Example 2: Content Pipeline
        print("\n\n2️⃣  Content Pipeline Example")
        print("-" * 60)
        await example_content_pipeline(user_id, db)

        # Example 3: Customer Onboarding
        print("\n\n3️⃣  Customer Onboarding Example")
        print("-" * 60)
        await example_customer_onboarding(user_id, db, "john@example.com")

        print("\n\n✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
