import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class CheckrConfig:
    """Configuration class for Checkr API credentials and settings."""
    access_token: str
    expires_in: int
    token_type: str
    base_url: str
    token_endpoint: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_issued_at: datetime = None
    
    def __post_init__(self):
        if self.token_issued_at is None:
            self.token_issued_at = datetime.now()
    
    def is_token_expired(self) -> bool:
        """Check if the access token has expired (with 5-minute buffer)."""
        if self.token_issued_at is None:
            return True
        
        expiry_time = self.token_issued_at + timedelta(seconds=self.expires_in - 300)
        return datetime.now() > expiry_time
    
    def get_token_url(self) -> str:
        """Get the complete token endpoint URL."""
        return f"{self.base_url}{self.token_endpoint}"

class CheckrAPIClient:
    """
    Checkr Trust API Client for instant criminal background checks.
    
    This client handles authentication, token management, and provides methods
    to create and retrieve instant criminal check results according to the
    official Checkr Trust API documentation.
    """
    
    def __init__(self, config_file_path: str = "checkr_config.json"):
        """
        Initialize the Checkr API client.
        
        Args:
            config_file_path: Path to JSON configuration file with API credentials
        """
        self.config = self._load_configuration(config_file_path)
        self.session = requests.Session()
        self._setup_session_headers()
        
        print(f"✓ Checkr API Client initialized successfully")
        print(f"  Base URL: {self.config.base_url}")
        print(f"  Token expires in: {self.config.expires_in} seconds")
    
    def _load_configuration(self, config_path: str) -> CheckrConfig:
        """
        Load and validate Checkr API configuration from JSON file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Validated CheckrConfig object
        """
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        
        # Validate required fields
        required_fields = ["access_token", "expires_in", "token_type"]
        missing_fields = [field for field in required_fields if field not in config_data]
        if missing_fields:
            raise ValueError(f"Missing required fields in config: {missing_fields}")
        
        # Set default values for optional fields
        base_url = config_data.get("base_url", "https://api.checkrtrust.com")
        token_endpoint = config_data.get("token_endpoint", "/v1/accounts/token")
        
        return CheckrConfig(
            access_token=config_data["access_token"],
            expires_in=config_data["expires_in"],
            token_type=config_data["token_type"],
            base_url=base_url,
            token_endpoint=token_endpoint,
            client_id=config_data.get("client_id"),
            client_secret=config_data.get("client_secret")
        )
    
    def _setup_session_headers(self):
        """Configure session headers for API authentication."""
        self.session.headers.update({
            "Authorization": f"{self.config.token_type} {self.config.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CheckrTrustAPIClient/1.0"
        })
    
    def _validate_token(self):
        """
        Validate that the access token is still valid.
        
        Raises:
            Exception: If token has expired
        """
        if self.config.is_token_expired():
            raise Exception(
                f"Access token expired. Token was issued at {self.config.token_issued_at}, "
                f"expires after {self.config.expires_in} seconds. Please refresh the token."
            )
    
    def _format_date(self, date_str: str) -> str:
        """
        Convert date from YYYY-MM-DD format to YYYYMMDD format required by API.
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Date in YYYYMMDD format
        """
        if not date_str:
            return ""
        
        # If already in YYYYMMDD format, return as-is
        if len(date_str) == 8 and date_str.isdigit():
            return date_str
        
        # Convert from YYYY-MM-DD to YYYYMMDD
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%Y%m%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD or YYYYMMDD")
    
    def _make_request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an authenticated HTTP request to the Checkr API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            payload: Request body data
            
        Returns:
            JSON response as dictionary
        """
        self._validate_token()
        
        url = f"{self.config.base_url}{endpoint}"
        
        print(f"→ {method.upper()} {url}")
        if payload:
            print(f"  Payload: {json.dumps(payload, indent=2)}")
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=payload)
            elif method.upper() == "POST":
                response = self.session.post(url, json=payload)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=payload)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            print(f"  Response: {response.status_code}")
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse and return JSON
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors with detailed information
            error_details = f"HTTP {response.status_code}: {e}"
            try:
                api_error = response.json()
                error_details += f"\nAPI Response: {json.dumps(api_error, indent=2)}"
            except:
                error_details += f"\nResponse Text: {response.text}"
            
            print(f"❌ {error_details}")
            raise Exception(error_details)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {e}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response: {e}\nResponse: {response.text}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def refresh_token(self) -> Dict[str, Any]:
        """
        Refresh the access token using client credentials.
        
        Returns:
            New token information
        """
        if not self.config.client_id or not self.config.client_secret:
            raise ValueError("client_id and client_secret required for token refresh")
        
        token_url = self.config.get_token_url()
        
        credentials = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        # Create temporary session for token request
        temp_session = requests.Session()
        temp_session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        try:
            print(f"🔄 Refreshing token at {token_url}")
            response = temp_session.post(token_url, json=credentials)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Update configuration with new token
            self.config.access_token = token_data["access_token"]
            self.config.expires_in = token_data["expires_in"]
            self.config.token_type = token_data["token_type"]
            self.config.token_issued_at = datetime.now()
            
            # Update session headers
            self._setup_session_headers()
            
            print("✓ Token refreshed successfully")
            return token_data
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Token refresh failed: {e}"
            if hasattr(e, 'response') and e.response:
                error_msg += f"\nResponse: {e.response.text}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def create_instant_criminal_check(self,
                                    first_name: str,
                                    last_name: str,
                                    dob: Optional[str] = None,
                                    middle_name: Optional[str] = None,
                                    ssn: Optional[str] = None,
                                    email: Optional[str] = None,
                                    phone: Optional[str] = None,
                                    address: Optional[Dict[str, str]] = None,
                                    reference_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create an instant criminal background check according to Checkr Trust API documentation.
        
        Args:
            first_name: Person's first name (required)
            last_name: Person's last name (required)
            dob: Date of birth in YYYY-MM-DD or YYYYMMDD format (optional but recommended)
            middle_name: Middle name (optional)
            ssn: Social Security Number in XXX-XX-XXXX format (optional)
            email: Email address (optional)
            phone: Phone in +[country code][number] format (optional)
            address: Address dict with street, city, state, zip_code (optional)
            reference_id: Your reference ID for the check (optional)
            
        Returns:
            Complete API response with check results
        """
        
        # Build the request payload according to API documentation
        check_data = {
            "first_name": first_name.strip(),
            "last_name": last_name.strip()
        }
        
        # Add optional fields if provided
        if middle_name:
            check_data["middle_name"] = middle_name.strip()
        
        if dob:
            # Convert date to YYYYMMDD format required by API
            check_data["dob"] = self._format_date(dob)
        
        if ssn:
            check_data["ssn"] = ssn.strip()
        
        if email:
            check_data["email"] = email.strip()
        
        if phone:
            check_data["phone"] = phone.strip()
        
        if address:
            # Format address according to API documentation
            address_data = {}
            if address.get("street"):
                address_data["street"] = address["street"].strip()
            if address.get("city"):
                address_data["city"] = address["city"].strip()
            if address.get("state"):
                address_data["state"] = address["state"].strip()
            if address.get("zip_code"):
                address_data["zip_code"] = address["zip_code"].strip()
            
            if address_data:  # Only add if we have address data
                check_data["address"] = address_data
        
        if reference_id:
            check_data["reference_id"] = reference_id.strip()
        
        print(f"🔍 Creating instant criminal check for: {first_name} {last_name}")
        
        # Make API request - Checkr Trust API returns results immediately for instant checks
        response = self._make_request("POST", "/v1/checks", check_data)
        
        check_id = response.get("id")
        if check_id:
            print(f"✓ Check created with ID: {check_id}")
        
        return response
    
    def get_check_status(self, check_id: str) -> Dict[str, Any]:
        """
        Retrieve a background check by its ID.
        
        Args:
            check_id: The ID of the check to retrieve
            
        Returns:
            Check data and results
        """
        print(f"📊 Getting check: {check_id}")
        
        response = self._make_request("GET", f"/v1/checks/{check_id}")
        
        return response
    
    def run_instant_criminal_check(self,
                                 first_name: str,
                                 last_name: str,
                                 dob: Optional[str] = None,
                                 middle_name: Optional[str] = None,
                                 ssn: Optional[str] = None,
                                 email: Optional[str] = None,
                                 phone: Optional[str] = None,
                                 address: Optional[Dict[str, str]] = None,
                                 reference_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a complete instant criminal check workflow.
        
        Note: Checkr Trust instant criminal checks return results immediately,
        so no polling is required.
        
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
            Complete check results
        """
        
        print("🚀 Starting instant criminal check workflow")
        
        # Create the check - results are returned immediately
        results = self.create_instant_criminal_check(
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
        
        print("✓ Instant criminal check completed")
        return results
    
    def get_token_info(self) -> Dict[str, Any]:
        """
        Get detailed information about the current access token.
        
        Returns:
            Token status and configuration information
        """
        time_remaining = max(0, self.config.expires_in - 
                           (datetime.now() - self.config.token_issued_at).total_seconds())
        
        return {
            "token_type": self.config.token_type,
            "expires_in_seconds": self.config.expires_in,
            "issued_at": self.config.token_issued_at.isoformat() if self.config.token_issued_at else None,
            "is_expired": self.config.is_token_expired(),
            "time_remaining_seconds": int(time_remaining),
            "time_remaining_minutes": round(time_remaining / 60, 1),
            "base_url": self.config.base_url,
            "token_endpoint": self.config.token_endpoint
        }


def main():
    """Main function demonstrating the Checkr API client usage."""
    
    try:
        print("=" * 70)
        print("CHECKR TRUST INSTANT CRIMINAL CHECK API CLIENT")
        print("=" * 70)
        
        # Initialize client
        client = CheckrAPIClient("checkr_config.json")
        
        # Show token information
        print("\n📋 TOKEN INFORMATION:")
        token_info = client.get_token_info()
        for key, value in token_info.items():
            print(f"  {key}: {value}")
        
        # Sample person data for testing
        person = {
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1990-01-15",  # Will be converted to 19900115
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
            "reference_id": "test-check-001"
        }
        
        print(f"\n👤 TARGET PERSON:")
        print(f"  Name: {person['first_name']} {person.get('middle_name', '')} {person['last_name']}")
        print(f"  DOB: {person['dob']}")
        print(f"  SSN: {person.get('ssn', 'Not provided')}")
        print(f"  Email: {person.get('email', 'Not provided')}")
        print(f"  Phone: {person.get('phone', 'Not provided')}")
        if person.get('address'):
            addr = person['address']
            print(f"  Address: {addr.get('street')}, {addr.get('city')}, {addr.get('state')} {addr.get('zip_code')}")
        print(f"  Reference ID: {person.get('reference_id', 'Not provided')}")
        
        print("\n" + "=" * 70)
        print("RUNNING INSTANT CRIMINAL CHECK")
        print("=" * 70)
        
        # Run the instant criminal check
        results = client.run_instant_criminal_check(
            first_name=person["first_name"],
            last_name=person["last_name"],
            dob=person.get("dob"),
            middle_name=person.get("middle_name"),
            ssn=person.get("ssn"),
            email=person.get("email"),
            phone=person.get("phone"),
            address=person.get("address"),
            reference_id=person.get("reference_id")
        )
        
        print("\n" + "=" * 70)
        print("INSTANT CRIMINAL CHECK RESULTS")
        print("=" * 70)
        print(json.dumps(results, indent=2))
        
        # Summary of results
        print("\n" + "=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        
        check_id = results.get("id", "Unknown")
        check_type = results.get("check_type", "Unknown")
        created_at = results.get("created_at", "Unknown")
        completed_at = results.get("completed_at", "Unknown")
        results_data = results.get("results", [])
        
        print(f"Check ID: {check_id}")
        print(f"Check Type: {check_type}")
        print(f"Created: {created_at}")
        print(f"Completed: {completed_at}")
        print(f"Number of result categories: {len(results_data)}")
        
        for result in results_data:
            category = result.get("category", "Unknown")
            cases = result.get("cases", [])
            print(f"  - {category}: {len(cases)} case(s)")
        
        print("\n" + "=" * 70)
        print("WORKFLOW COMPLETED SUCCESSFULLY ✓")
        print("=" * 70)
        
    except FileNotFoundError:
        print("❌ Configuration file 'checkr_config.json' not found")
        print("\n📝 Please create the file with this structure:")
        example_config = {
            "base_url": "https://api.checkrtrust.com",
            "token_endpoint": "/v1/accounts/token", 
            "access_token": "your_jwt_token_here",
            "expires_in": 86400,
            "token_type": "Bearer",
            "client_id": "your_client_id_here",
            "client_secret": "your_client_secret_here"
        }
        print(json.dumps(example_config, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print("\n🔍 Full traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    main()