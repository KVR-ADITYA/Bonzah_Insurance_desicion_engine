import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

class RiskLevel(Enum):
    IGNORED = "Ignored"
    LOW = "Low"
    MEDIUM = "Medium" 
    HIGH = "High"
    CLEAN = "Clean"

@dataclass
class ProcessedCase:
    case_number: str
    charge_description: str
    offense_date: str
    charge_type: str
    disposition: str
    category: str
    subcategory: str
    risk_level: RiskLevel
    risk_score: float
    reason: str
    
class CriminalCheckProcessor:
    def __init__(self, config_file_path: str = "config.json"):
        """Initialize the processor with configuration from JSON file."""
        self.config = self._load_config(config_file_path)
        self.lookback_years = self.config["search_parameters"]["lookback_period"]["selected_period"]
        self.cutoff_date = datetime.now() - timedelta(days=self.lookback_years * 365)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in configuration file: {config_path}")
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string in YYYYMMDD format."""
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYYMMDD.")
    
    def _is_within_lookback(self, offense_date: str) -> bool:
        """Check if offense date is within the configured lookback period."""
        try:
            offense_dt = self._parse_date(offense_date)
            return offense_dt >= self.cutoff_date
        except ValueError:
            return False
    
    def _is_record_category_enabled(self, category: str) -> bool:
        """Check if the record category is enabled in configuration."""
        categories = self.config["record_categories"]["categories"]
        for cat in categories:
            if cat["category"].lower() == category.lower():
                return cat["enabled"]
        return False
    
    def _is_charge_type_enabled(self, charge_type: str) -> bool:
        """Check if the charge type is enabled in configuration."""
        charge_types = self.config["charge_classification"]["types"]
        for ct in charge_types:
            if ct["input_key"].lower() == charge_type.lower():
                return ct["enabled"]
        return False
    
    def _is_disposition_enabled(self, disposition: str) -> bool:
        """Check if the disposition type is enabled in configuration."""
        dispositions = self.config["disposition_filters"]["dispositions"]
        for disp in dispositions:
            if disp["input_key"].lower() == disposition.lower():
                return disp["enabled"]
        return False
    
    def _get_risk_category_weight(self, category: str) -> float:
        """Get the base weight for a risk category."""
        risk_categories = self.config["risk_scoring"]["categories"]
        for cat in risk_categories:
            if cat["category"].lower() == category.lower():
                return cat["base_weight"]
        return 1.0  # Default weight
    
    def _get_charge_type_weight(self, charge_type: str) -> int:
        """Get the severity weight for a charge type."""
        charge_types = self.config["charge_classification"]["types"]
        for ct in charge_types:
            if ct["input_key"].lower() == charge_type.lower():
                return ct["severity_weight"]
        return 1  # Default weight
    
    def _get_disposition_risk_impact(self, disposition: str) -> str:
        """Get the risk impact level for a disposition."""
        dispositions = self.config["disposition_filters"]["dispositions"]
        for disp in dispositions:
            if disp["input_key"].lower() == disposition.lower():
                return disp["risk_impact"]
        return "low"  # Default impact
    
    def _get_csv_risk_score(self, category: str, subcategory: str) -> str:
        """Get risk score from CSV data based on category and subcategory."""
        # This is a simplified mapping based on the CSV data analysis
        # You should load this from the actual CSV files for production use
        
        risk_mapping = {
            # Vehicles & Traffic category mappings
            ("vehicles & traffic", "license"): "High",
            ("vehicles & traffic", "license & registration"): "High", 
            ("vehicles & traffic", "speeding"): "Low",
            ("vehicles & traffic", "traffic violations"): "Low",
            ("vehicles & traffic", "reckless driving"): "Med",
            
            # Other categories
            ("criminal intent", "accessory"): "Low",
            ("criminal intent", "court orders"): "Med",
            ("violence", ""): "High",
            ("sexual", ""): "High",
            ("homicide", ""): "High",
            ("fraud & deception", ""): "Med",
            ("drugs & alcohol", ""): "Med",
            ("theft & property", ""): "Med",
            ("security", ""): "High",
            ("statutory", ""): "Low",
            ("unclassified", ""): "High"
        }
        
        # Try exact match first
        key = (category.lower(), subcategory.lower())
        if key in risk_mapping:
            return risk_mapping[key]
        
        # Try category-only match
        key = (category.lower(), "")
        if key in risk_mapping:
            return risk_mapping[key]
        
        # Default based on category
        high_risk_categories = ["violence", "sexual", "homicide", "security", "unclassified"]
        if category.lower() in high_risk_categories:
            return "High"
        
        return "Med"  # Default to medium risk

    def _calculate_risk_score(self, charge: Dict[str, Any], offense_date: str) -> float:
        """Calculate risk score for a charge based on CSV risk data and configuration."""
        category = charge.get("category", "Unclassified")
        subcategory = charge.get("subcategory", "")
        
        # Get risk level from CSV data
        csv_risk_level = self._get_csv_risk_score(category, subcategory)
        
        # Convert CSV risk level to base score
        risk_base_scores = {
            "High": 30,
            "Med": 15, 
            "Low": 5,
            "Unscored": 10
        }
        
        base_score = risk_base_scores.get(csv_risk_level, 15)
        
        # Special handling for unclassified
        if category.lower() == "unclassified":
            base_score = 35  # Even higher for unclassified
        
        # Get charge type weight multiplier
        charge_type = charge.get("type", "unknown")
        charge_weight = self._get_charge_type_weight(charge_type)
        
        # Get disposition impact multiplier
        disposition = charge.get("dispositions", [{}])[0].get("disposition_type", "unknown")
        disposition_impact = self._get_disposition_risk_impact(disposition)
        
        # Apply multipliers
        impact_multipliers = {"high": 1.5, "medium": 1.2, "low": 1.0, "none": 0.5}
        disposition_multiplier = impact_multipliers.get(disposition_impact, 1.0)
        
        # Calculate final score
        final_score = base_score * (charge_weight / 2) * disposition_multiplier
        
        # Apply recency factor
        try:
            offense_dt = self._parse_date(offense_date)
            years_ago = (datetime.now() - offense_dt).days / 365
            
            if years_ago <= 1:
                recency_factor = 1.5
            elif years_ago <= 3:
                recency_factor = 1.2
            elif years_ago <= 5:
                recency_factor = 1.0
            else:
                recency_factor = 0.8
                
            final_score *= recency_factor
        except ValueError:
            pass  # Use base score without recency adjustment
        
        return round(final_score, 2)
    
    def _determine_risk_level(self, risk_score: float, category: str) -> RiskLevel:
        """Determine risk level based on score and category."""
        if category.lower() == "unclassified" and risk_score > 0:
            return RiskLevel.HIGH
        
        thresholds = self.config["scoring_rules"]["thresholds"]
        
        if risk_score >= thresholds["critical_risk"]["min"]:
            return RiskLevel.HIGH
        elif risk_score >= thresholds["high_risk"]["min"]:
            return RiskLevel.HIGH
        elif risk_score >= thresholds["medium_risk"]["min"]:
            return RiskLevel.MEDIUM
        elif risk_score >= thresholds["low_risk"]["min"]:
            return RiskLevel.LOW
        else:
            return RiskLevel.LOW
    
    def _process_charge(self, charge: Dict[str, Any], case_number: str) -> Tuple[ProcessedCase, bool]:
        """Process a single charge and return ProcessedCase and whether it should be included."""
        offense_date = charge.get("offense_date", "")
        charge_type = charge.get("type", "unknown")
        category = charge.get("category", "unclassified")
        subcategory = charge.get("subcategory", "")
        description = charge.get("description", "")
        disposition = charge.get("dispositions", [{}])[0].get("disposition_type", "unknown")
        
        # Check if within lookback period
        if not self._is_within_lookback(offense_date):
            processed_case = ProcessedCase(
                case_number=case_number,
                charge_description=description,
                offense_date=offense_date,
                charge_type=charge_type,
                disposition=disposition,
                category=category,
                subcategory=subcategory,
                risk_level=RiskLevel.IGNORED,
                risk_score=0.0,
                reason=f"Outside {self.lookback_years}-year lookback period"
            )
            return processed_case, False
        
        # Check if charge type is enabled
        if not self._is_charge_type_enabled(charge_type):
            processed_case = ProcessedCase(
                case_number=case_number,
                charge_description=description,
                offense_date=offense_date,
                charge_type=charge_type,
                disposition=disposition,
                category=category,
                subcategory=subcategory,
                risk_level=RiskLevel.IGNORED,
                risk_score=0.0,
                reason=f"Charge type '{charge_type}' not enabled in configuration"
            )
            return processed_case, False
        
        # Check if disposition is enabled
        if not self._is_disposition_enabled(disposition):
            processed_case = ProcessedCase(
                case_number=case_number,
                charge_description=description,
                offense_date=offense_date,
                charge_type=charge_type,
                disposition=disposition,
                category=category,
                subcategory=subcategory,
                risk_level=RiskLevel.IGNORED,
                risk_score=0.0,
                reason=f"Disposition '{disposition}' not enabled in configuration"
            )
            return processed_case, False
        
        # Calculate risk score and determine level
        risk_score = self._calculate_risk_score(charge, offense_date)
        risk_level = self._determine_risk_level(risk_score, category)
        
        processed_case = ProcessedCase(
            case_number=case_number,
            charge_description=description,
            offense_date=offense_date,
            charge_type=charge_type,
            disposition=disposition,
            category=category,
            subcategory=subcategory,
            risk_level=risk_level,
            risk_score=risk_score,
            reason="Processed successfully"
        )
        
        return processed_case, True
    
    def process_criminal_check(self, data: Dict[str, Any]) -> Dict[str, List[ProcessedCase]]:
        """
        Process criminal check data and categorize cases by risk level.
        
        Args:
            data: Criminal check data in Checkr Trust API format
            
        Returns:
            Dictionary with risk levels as keys and lists of ProcessedCase as values
        """
        results = {
            "Ignored": [],
            "Low": [],
            "Medium": [],
            "High": [],
            "Clean": []
        }
        
        # Check if input data has results
        if "results" not in data or not data["results"]:
            results["Clean"].append(ProcessedCase(
                case_number="N/A",
                charge_description="No criminal records found",
                offense_date="N/A",
                charge_type="N/A",
                disposition="N/A",
                category="N/A",
                subcategory="N/A",
                risk_level=RiskLevel.CLEAN,
                risk_score=0.0,
                reason="No criminal history found"
            ))
            return results
        
        processed_any = False
        
        for result in data["results"]:
            category = result.get("category", "")
            
            # Check if record category is enabled
            if not self._is_record_category_enabled(category):
                continue
                
            cases = result.get("cases", [])
            for case in cases:
                case_number = case.get("case_number", "unknown")
                charges = case.get("charges", [])
                
                for charge in charges:
                    processed_case, should_include = self._process_charge(charge, case_number)
                    
                    if processed_case.risk_level == RiskLevel.IGNORED:
                        results["Ignored"].append(processed_case)
                    else:
                        results[processed_case.risk_level.value].append(processed_case)
                        if should_include:
                            processed_any = True
        
        # If no cases were processed (all ignored) and no active cases, mark as clean
        if not processed_any and not any(results[level] for level in ["Low", "Medium", "High"]):
            if not results["Ignored"]:  # Only if nothing was ignored either
                results["Clean"].append(ProcessedCase(
                    case_number="N/A",
                    charge_description="No qualifying criminal records found",
                    offense_date="N/A",
                    charge_type="N/A",
                    disposition="N/A",
                    category="N/A",
                    subcategory="N/A",
                    risk_level=RiskLevel.CLEAN,
                    risk_score=0.0,
                    reason="No records meet the configured criteria"
                ))
        
        return results
    
    def get_summary(self, processed_results: Dict[str, List[ProcessedCase]]) -> Dict[str, Any]:
        """Generate a summary of the processed results."""
        summary = {
            "total_cases": sum(len(cases) for cases in processed_results.values()),
            "risk_distribution": {},
            "highest_risk_score": 0.0,
            "recommendations": []
        }
        
        for risk_level, cases in processed_results.items():
            summary["risk_distribution"][risk_level] = len(cases)
            if cases:
                max_score = max(case.risk_score for case in cases)
                summary["highest_risk_score"] = max(summary["highest_risk_score"], max_score)
        
        # Generate recommendations
        if processed_results["High"]:
            summary["recommendations"].append("High-risk cases require immediate review")
        if processed_results["Medium"]:
            summary["recommendations"].append("Medium-risk cases should be evaluated")
        if processed_results["Clean"]:
            summary["recommendations"].append("No concerning criminal history found")
        if processed_results["Ignored"]:
            summary["recommendations"].append(f"{len(processed_results['Ignored'])} cases ignored due to filters")
            
        return summary


# Example usage
if __name__ == "__main__":
    # Sample data as provided
    sample_data = {
        "id": "5448da6a-a432-4a6e-9843-641d5e2fdd80",
        "results": [
            {
                "category": "Criminal/traffic",
                "cases": [
                    {
                        "case_number": "16-2016-CT-009299-AXXX-MA",
                        "charges": [
                            {
                                "offense_date": "20160623",
                                "type": "unknown",
                                "dispositions": [{"disposition_type": "Unclassified"}],
                                "category": "unclassified"
                            }
                        ]
                    }
                ]
            },
            {
                "category": "Criminal/traffic", 
                "cases": [
                    {
                        "case_number": "2022TR030504 A",
                        "charges": [
                            {
                                "description": "SPEED/70 INTERSTTE (REQUIRES SPEED)",
                                "offense_date": "20221201",
                                "type": "petty_offense",
                                "dispositions": [{"disposition_type": "Conviction"}],
                                "category": "Vehicles & Traffic",
                                "subcategory": "Speeding"
                            }
                        ]
                    }
                ]
            },
            {
                "category": "Criminal/traffic",
                "cases": [
                    {
                        "case_number": "16-2016-CT-009298-AXXX-MA", 
                        "charges": [
                            {
                                "description": "LICENSE; KNOWINGLY OPER VEH W- DL SUSP, CANCELLED, REVOKED",
                                "offense_date": "20160623",
                                "type": "misdemeanor",
                                "dispositions": [{"disposition_type": "Pending"}],
                                "category": "Vehicles & Traffic",
                                "subcategory": "License & Registration"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    # Initialize processor
    processor = CriminalCheckProcessor("config.json")
    
    # Process the data
    results = processor.process_criminal_check(sample_data)
    
    # Print results
    for risk_level, cases in results.items():
        print(f"\n{risk_level} Risk Cases ({len(cases)}):")
        for case in cases:
            print(f"  Case: {case.case_number}")
            print(f"  Description: {case.charge_description}")
            print(f"  Date: {case.offense_date}")
            print(f"  Type: {case.charge_type}")
            print(f"  Disposition: {case.disposition}")
            print(f"  Category: {case.category}")
            print(f"  Risk Score: {case.risk_score}")
            print(f"  Reason: {case.reason}")
            print()
    
    # Print summary
    summary = processor.get_summary(results)
    print("Summary:")
    print(json.dumps(summary, indent=2))