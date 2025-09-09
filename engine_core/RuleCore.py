import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

# Import the existing classes
from CheckrAPI import CheckrAPIClient
from CriminalCheck import CriminalCheckProcessor, ProcessedCase, RiskLevel

@dataclass
class RuleEngineResult:
    """Complete result from the rule engine including API data and risk assessment."""
    checkr_check_id: str
    checkr_response: Dict[str, Any]
    processed_cases: Dict[str, List[ProcessedCase]]
    summary: Dict[str, Any]
    execution_time_seconds: float
    person_info: Dict[str, str]
    recommendation: str
    overall_risk_level: RiskLevel

class RuleEngineError(Exception):
    """Custom exception for rule engine errors."""
    pass

class CriminalBackgroundRuleEngine:
    """
    Unified rule engine that combines Checkr API data retrieval with 
    criminal record risk assessment and processing.
    
    This engine handles the complete workflow from API calls to risk categorization
    based on configurable business rules.
    """
    
    def __init__(self, 
                 checkr_config_path: str = "checkr_config.json",
                 risk_config_path: str = "config.json"):
        """
        Initialize the rule engine with both API and risk assessment configurations.
        
        Args:
            checkr_config_path: Path to Checkr API configuration
            risk_config_path: Path to risk assessment configuration
        """
        self.start_time = None
        
        # Initialize both components
        try:
            self.api_client = CheckrAPIClient(checkr_config_path)
            print("✓ Checkr API client initialized")
        except Exception as e:
            raise RuleEngineError(f"Failed to initialize Checkr API client: {e}")
        
        try:
            self.risk_processor = CriminalCheckProcessor(risk_config_path)
            print("✓ Risk assessment processor initialized")
        except Exception as e:
            raise RuleEngineError(f"Failed to initialize risk processor: {e}")
    
    def _calculate_overall_risk(self, processed_cases: Dict[str, List[ProcessedCase]]) -> RiskLevel:
        """
        Calculate overall risk level based on processed cases.
        
        Args:
            processed_cases: Dictionary of risk levels and their cases
            
        Returns:
            Overall risk level for the person
        """
        # If any high risk cases, overall is high
        if processed_cases.get("High"):
            return RiskLevel.HIGH
        
        # If any medium risk cases, overall is medium
        if processed_cases.get("Medium"):
            return RiskLevel.MEDIUM
        
        # If any low risk cases, overall is low
        if processed_cases.get("Low"):
            return RiskLevel.LOW
        
        # If only ignored cases, consider as clean
        if processed_cases.get("Ignored") and not any(
            processed_cases.get(level) for level in ["High", "Medium", "Low"]
        ):
            return RiskLevel.CLEAN
        
        # If clean results
        if processed_cases.get("Clean"):
            return RiskLevel.CLEAN
        
        # Default to clean if no cases
        return RiskLevel.CLEAN
    
    def _generate_recommendation(self, 
                               overall_risk: RiskLevel, 
                               processed_cases: Dict[str, List[ProcessedCase]]) -> str:
        """
        Generate actionable recommendation based on risk assessment.
        
        Args:
            overall_risk: Overall risk level
            processed_cases: Processed case data
            
        Returns:
            Recommendation string
        """
        high_count = len(processed_cases.get("High", []))
        medium_count = len(processed_cases.get("Medium", []))
        low_count = len(processed_cases.get("Low", []))
        ignored_count = len(processed_cases.get("Ignored", []))
        
        if overall_risk == RiskLevel.HIGH:
            return (f"REJECT - High risk profile identified. {high_count} high-risk case(s) "
                   f"require immediate review and likely disqualification.")
        
        elif overall_risk == RiskLevel.MEDIUM:
            return (f"REVIEW REQUIRED - Medium risk profile. {medium_count} case(s) need "
                   f"manual review before making a decision.")
        
        elif overall_risk == RiskLevel.LOW:
            return (f"CONDITIONAL APPROVAL - Low risk profile. {low_count} minor case(s) "
                   f"identified but may be acceptable depending on role requirements.")
        
        elif overall_risk == RiskLevel.CLEAN:
            if ignored_count > 0:
                return (f"APPROVE - Clean background check. {ignored_count} case(s) were "
                       f"outside assessment criteria.")
            else:
                return "APPROVE - Clean background check with no concerning records found."
        
        else:
            return "MANUAL REVIEW - Unable to determine risk level automatically."
    
    def _format_person_info(self, **kwargs) -> Dict[str, str]:
        """Format person information for tracking."""
        return {
            "first_name": kwargs.get("first_name", ""),
            "last_name": kwargs.get("last_name", ""),
            "dob": kwargs.get("dob", ""),
            "reference_id": kwargs.get("reference_id", ""),
            "processed_at": datetime.now().isoformat()
        }
    
    def run_complete_background_check(self,
                                    first_name: str,
                                    last_name: str,
                                    dob: Optional[str] = None,
                                    middle_name: Optional[str] = None,
                                    ssn: Optional[str] = None,
                                    email: Optional[str] = None,
                                    phone: Optional[str] = None,
                                    address: Optional[Dict[str, str]] = None,
                                    reference_id: Optional[str] = None) -> RuleEngineResult:
        """
        Execute complete background check workflow including API call and risk assessment.
        
        Args:
            first_name: Person's first name (required)
            last_name: Person's last name (required)
            dob: Date of birth (optional but recommended)
            middle_name: Middle name (optional)
            ssn: Social Security Number (optional)
            email: Email address (optional)
            phone: Phone number (optional)
            address: Address information (optional)
            reference_id: Your reference ID (optional)
            
        Returns:
            Complete RuleEngineResult with API data and risk assessment
        """
        
        self.start_time = time.time()
        
        print("=" * 80)
        print("CRIMINAL BACKGROUND CHECK RULE ENGINE")
        print("=" * 80)
        
        # Format person info for tracking
        person_info = self._format_person_info(
            first_name=first_name,
            last_name=last_name,
            dob=dob,
            reference_id=reference_id
        )
        
        print(f"Processing: {first_name} {last_name}")
        if reference_id:
            print(f"Reference ID: {reference_id}")
        
        try:
            # Step 1: Get criminal records from Checkr API
            print("\n[STEP 1] Retrieving criminal records from Checkr API...")
            checkr_response = self.api_client.run_instant_criminal_check(
                first_name=first_name,
                last_name=last_name,
                dob=dob,
                middle_name=middle_name,
                ssn=ssn,
                email=email,
                phone=phone,
                address=address,
                reference_id=reference_id
            )
            
            checkr_check_id = checkr_response.get("id", "unknown")
            records_count = checkr_response.get("results_info", {}).get("records_found", 0)
            print(f"✓ Retrieved {records_count} criminal record(s) from Checkr")
            
            # Step 2: Process records through risk assessment engine
            print("\n[STEP 2] Processing records through risk assessment engine...")
            processed_cases = self.risk_processor.process_criminal_check(checkr_response)
            
            # Count processed cases
            total_processed = sum(len(cases) for cases in processed_cases.values())
            print(f"✓ Processed {total_processed} case(s) through risk engine")
            
            # Step 3: Generate summary and recommendations
            print("\n[STEP 3] Generating risk assessment and recommendations...")
            summary = self.risk_processor.get_summary(processed_cases)
            overall_risk = self._calculate_overall_risk(processed_cases)
            recommendation = self._generate_recommendation(overall_risk, processed_cases)
            
            execution_time = time.time() - self.start_time
            
            print(f"✓ Risk assessment completed in {execution_time:.2f} seconds")
            print(f"Overall Risk Level: {overall_risk.value}")
            print(f"Recommendation: {recommendation}")
            
            # Create complete result
            result = RuleEngineResult(
                checkr_check_id=checkr_check_id,
                checkr_response=checkr_response,
                processed_cases=processed_cases,
                summary=summary,
                execution_time_seconds=execution_time,
                person_info=person_info,
                recommendation=recommendation,
                overall_risk_level=overall_risk
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - self.start_time if self.start_time else 0
            error_msg = f"Rule engine execution failed after {execution_time:.2f} seconds: {e}"
            print(f"❌ {error_msg}")
            raise RuleEngineError(error_msg)
    
    def print_detailed_results(self, result: RuleEngineResult):
        """
        Print a detailed, formatted report of the background check results.
        
        Args:
            result: RuleEngineResult to display
        """
        
        print("\n" + "=" * 80)
        print("DETAILED BACKGROUND CHECK RESULTS")
        print("=" * 80)
        
        # Header information
        print(f"Person: {result.person_info['first_name']} {result.person_info['last_name']}")
        print(f"Check ID: {result.checkr_check_id}")
        print(f"Processed At: {result.person_info['processed_at']}")
        print(f"Execution Time: {result.execution_time_seconds:.2f} seconds")
        print(f"Overall Risk: {result.overall_risk_level.value}")
        print(f"Recommendation: {result.recommendation}")
        
        # Risk distribution
        print(f"\nRisk Distribution:")
        for risk_level, cases in result.processed_cases.items():
            print(f"  {risk_level}: {len(cases)} case(s)")
        
        # Detailed case breakdown
        for risk_level, cases in result.processed_cases.items():
            if cases:
                print(f"\n{risk_level.upper()} RISK CASES ({len(cases)}):")
                print("-" * 50)
                
                for i, case in enumerate(cases, 1):
                    print(f"{i}. Case: {case.case_number}")
                    print(f"   Description: {case.charge_description}")
                    print(f"   Date: {case.offense_date}")
                    print(f"   Type: {case.charge_type}")
                    print(f"   Disposition: {case.disposition}")
                    print(f"   Category: {case.category}")
                    if case.subcategory:
                        print(f"   Subcategory: {case.subcategory}")
                    print(f"   Risk Score: {case.risk_score}")
                    print(f"   Reason: {case.reason}")
                    print()
        
        # Summary statistics
        print("SUMMARY STATISTICS:")
        print("-" * 50)
        for key, value in result.summary.items():
            print(f"{key}: {value}")
        
        print("\n" + "=" * 80)
    
    def export_results_json(self, result: RuleEngineResult, filename: Optional[str] = None) -> str:
        """
        Export results to JSON file for record keeping.
        
        Args:
            result: RuleEngineResult to export
            filename: Optional filename, auto-generated if not provided
            
        Returns:
            Filename of exported file
        """
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            person_name = f"{result.person_info['first_name']}_{result.person_info['last_name']}"
            filename = f"background_check_{person_name}_{timestamp}.json"
        
        # Convert result to JSON-serializable format
        export_data = {
            "person_info": result.person_info,
            "checkr_check_id": result.checkr_check_id,
            "overall_risk_level": result.overall_risk_level.value,
            "recommendation": result.recommendation,
            "execution_time_seconds": result.execution_time_seconds,
            "summary": result.summary,
            "processed_cases": {
                risk_level: [
                    {
                        "case_number": case.case_number,
                        "charge_description": case.charge_description,
                        "offense_date": case.offense_date,
                        "charge_type": case.charge_type,
                        "disposition": case.disposition,
                        "category": case.category,
                        "subcategory": case.subcategory,
                        "risk_level": case.risk_level.value,
                        "risk_score": case.risk_score,
                        "reason": case.reason
                    }
                    for case in cases
                ]
                for risk_level, cases in result.processed_cases.items()
            },
            "checkr_response": result.checkr_response
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"✓ Results exported to: {filename}")
        return filename


def main():
    """Example usage of the Criminal Background Check Rule Engine."""
    
    try:
        # Initialize the rule engine
        engine = CriminalBackgroundRuleEngine(
            checkr_config_path="checkr_config.json",
            risk_config_path="config.json"
        )
        
        # Example person data
        person_data = {
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-15",
            "middle_name": "Michael",
            "ssn": "123-45-6789",
            "email": "john.doe@example.com",
            "phone": "+14155552671",
            "address": {
                "street": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip_code": "12345"
            },
            "reference_id": "employee-screening-001"
        }
        
        # Run complete background check
        result = engine.run_complete_background_check(**person_data)
        
        # Display detailed results
        engine.print_detailed_results(result)
        
        # Export results for record keeping
        exported_file = engine.export_results_json(result)
        
        print(f"\nBackground check completed successfully!")
        print(f"Final recommendation: {result.recommendation}")
        print(f"Results saved to: {exported_file}")
        
    except RuleEngineError as e:
        print(f"Rule Engine Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()