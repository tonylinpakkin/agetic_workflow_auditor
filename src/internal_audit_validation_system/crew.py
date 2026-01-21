import os
import json

from crewai import LLM
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import (
	SerperDevTool
)
from internal_audit_validation_system.tools.custom_tool import (
	SecureWebScraperTool,
	RobustFileReadTool,
	PDFDownloadTool,
	MarkdownToPDFTool
)






@CrewBase
class InternalAuditValidationSystemCrew:
    """InternalAuditValidationSystem crew"""

    def __init__(self, timestamp: str = None):
        """Initialize the crew with optional timestamp for output path configuration.

        Args:
            timestamp: Timestamp string (YYYYMMDD_HHMMSS) to use for output directory.
                      If provided, all task output files will be saved to output/{timestamp}/
        """
        # The CrewBase decorator's __init__ will call our original __init__ via super(),
        # then load configurations. We need to update paths AFTER that happens.
        # So we store the timestamp and use __setattr__ hook or just update immediately
        # after storing it, knowing the decorator will process everything.
        self._timestamp = timestamp

        # HACK: Use a flag to trigger path update after decorator finishes init
        self._needs_path_update = timestamp is not None

    def __setattr__(self, name, value):
        """Intercept attribute setting to update paths after initialization completes."""
        super().__setattr__(name, value)

        # After the decorator finishes __init__, it sets various attributes.
        # We detect when tasks_config is set and update paths then.
        if name == 'tasks_config' and getattr(self, '_needs_path_update', False):
            self._needs_path_update = False
            if hasattr(self, '_timestamp') and self._timestamp:
                self._update_output_paths(self._timestamp)

    def _update_output_paths(self, timestamp: str):
        """Update task output file paths to use timestamped subdirectory.

        Args:
            timestamp: Timestamp string to use in output paths
        """
        task_output_mapping = {
            "retrieve_hkma_policies": "hkma_policy_retrieval",
            "retrieve_sfc_policies": "sfc_policy_retrieval",
            "retrieve_relevant_policies": "policy_retrieval_aggregated",
            "reflect_policy_retrieval": "retrieval_review",
            "revise_policy_retrieval": "policy_retrieval_final",
            "analyze_compliance_status": "compliance_analysis",
            "prepare_peer_review_package": "peer_review_package",
            "reflection_of_compliance_status": "compliance_reflection",
            "review_compliance_analysis": "review_report",
        }

        for task_key, base_filename in task_output_mapping.items():
            if task_key in self.tasks_config:
                # Update to timestamped path: output/TIMESTAMP/filename.md
                self.tasks_config[task_key]["output_file"] = f"output/{timestamp}/{base_filename}.md"


    @agent
    def hkma_policy_retrieval_specialist(self) -> Agent:

        
        return Agent(
            config=self.agents_config["hkma_policy_retrieval_specialist"],


			tools=[
				RobustFileReadTool(),
				SecureWebScraperTool(),
				PDFDownloadTool(),
				SerperDevTool(n_results=10)
            ],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
                max_retries=5,
                timeout=120,
            ),
            
        )

    @agent
    def sfc_policy_retrieval_specialist(self) -> Agent:

        
        return Agent(
            config=self.agents_config["sfc_policy_retrieval_specialist"],


			tools=[
				RobustFileReadTool(),
				SecureWebScraperTool(),
				PDFDownloadTool(),
				SerperDevTool(n_results=10)
            ],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
                max_retries=5,
                timeout=120,
            ),
            
        )

    @agent
    def policy_aggregator(self) -> Agent:


        return Agent(
            config=self.agents_config["policy_aggregator"],


            tools=[
                # SerperDevTool added to enable URL verification and prevent hallucination
                # when the agent needs to add new policy sources during revision
                SerperDevTool(n_results=10),
                # MarkdownToPDFTool allows agent to convert final markdown reports to PDF
                MarkdownToPDFTool()
            ],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=15,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
                max_retries=5,
                timeout=120,
            ),
            
        )

    @agent
    def policy_retrieval_specialist(self) -> Agent:

        
        return Agent(
            config=self.agents_config["policy_retrieval_specialist"],


			tools=[
				RobustFileReadTool(),
				SecureWebScraperTool(),
				PDFDownloadTool(),
				SerperDevTool(n_results=10)
            ],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
                max_retries=5,
                timeout=120,
            ),
            
        )
    
    @agent
    def audit_analysis_expert(self) -> Agent:


        return Agent(
            config=self.agents_config["audit_analysis_expert"],


            tools=[
			# RobustFileReadTool()
            ],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
                max_retries=5,
                timeout=120,
            ),
            
        )
    
    @agent
    def peer_review_coordinator(self) -> Agent:

        
        return Agent(
            config=self.agents_config["peer_review_coordinator"],
            
            
            tools=[
				# RobustFileReadTool()
            ],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=25,
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
                max_retries=5,
                timeout=120,
            ),
            
        )
    
    @agent
    def senior_audit_reviewer(self) -> Agent:


        return Agent(
            config=self.agents_config["senior_audit_reviewer"],


            tools=[
                # No tools needed - this agent reviews content provided via context
                # from previous tasks, not external sources
            ],
            reasoning=False,
            max_reasoning_attempts=None,
            inject_date=True,
            allow_delegation=False,
            max_iter=15,  # Reduced from 25 since no external research needed
            max_rpm=None,
            max_execution_time=None,
            llm=LLM(
                model="gpt-4o-mini",
                temperature=0.7,
                max_retries=5,
                timeout=120,
            ),

        )
    

    
    @task
    def retrieve_relevant_policies(self) -> Task:
        # Override description to enforce consolidation-only behavior
        cfg = dict(self.tasks_config["retrieve_relevant_policies"])
        cfg["description"] = (
            "Consolidate the HKMA and SFC policy retrieval outputs for \"{audit_observation}\" "
            "into a single, deduplicated table.\n\n"
            "Work ONLY from the context provided by retrieve_hkma_policies and retrieve_sfc_policies. "
            "Do not perform any new retrieval, web search, file reads, or external lookups.\n\n"
            "Your consolidation should:\n"
            "- Merge both input tables and remove duplicates (same Source Name + Section/Clause + URL)\n"
            "- Normalize section/paragraph identifiers and keep key excerpts verbatim (≤ 1 sentence)\n"
            "- Ensure provenance completeness (paths/URLs, effective dates); use \"Unknown\" only if truly unavailable\n"
            "- Provide a short bullet list of the top three most critical requirements across both regulators\n"
            "- Add a one-line note on coverage balance (HKMA vs SFC) and call out any gaps"
        )
        return Task(
            config=cfg,
            markdown=True,


        )

    @task
    def retrieve_hkma_policies(self) -> Task:
        return Task(
            config=self.tasks_config["retrieve_hkma_policies"],
            markdown=True,


        )

    @task
    def retrieve_sfc_policies(self) -> Task:
        return Task(
            config=self.tasks_config["retrieve_sfc_policies"],
            markdown=True,


        )
    
    @task
    def reflect_policy_retrieval(self) -> Task:
        return Task(
            config=self.tasks_config["reflect_policy_retrieval"],
            markdown=True,
        )

    @task
    def revise_policy_retrieval(self) -> Task:
        return Task(
            config=self.tasks_config["revise_policy_retrieval"],
            markdown=True,
        )

    @task
    def analyze_compliance_status(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_compliance_status"],
            markdown=True,
            
            
        )
    
    @task
    def review_compliance_analysis(self) -> Task:
        return Task(
            config=self.tasks_config["review_compliance_analysis"],
            markdown=True,
            
            
        )
    
    @task
    def prepare_peer_review_package(self) -> Task:
        return Task(
            config=self.tasks_config["prepare_peer_review_package"],
            markdown=True,
            
            
        )
    
    @task
    def reflection_of_compliance_status(self) -> Task:
        return Task(
            config=self.tasks_config["reflection_of_compliance_status"],
            markdown=True,
            
            
        )
    

    @crew
    def crew(self) -> Crew:
        """Creates the InternalAuditValidationSystem crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=[
                self.retrieve_hkma_policies(),
                self.retrieve_sfc_policies(),
                self.retrieve_relevant_policies(),
                self.reflect_policy_retrieval(),
                self.revise_policy_retrieval(),
                # self.analyze_compliance_status(),
                # self.review_compliance_analysis()
            ],  # Run only these tasks
            # tasks=self.tasks,  # Uncomment to run all tasks
            process=Process.sequential,
            verbose=True,
            max_rpm=10,  # Limit to 10 requests per minute to avoid rate limits
        )
