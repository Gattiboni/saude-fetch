import requests
import sys
import os
import time
import tempfile
import csv
from datetime import datetime

class SaudeFetchAPITester:
    def __init__(self):
        # Get the public backend URL from frontend env
        frontend_env_path = "/app/frontend/.env"
        self.base_url = None
        
        try:
            with open(frontend_env_path, 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        backend_path = line.split('=', 1)[1].strip().strip('"')
                        # Since it's "/api", we need to construct the full URL
                        # In production, this would be the external URL, but for testing we'll use localhost
                        self.base_url = f"http://localhost:8001{backend_path}"
                        break
        except Exception as e:
            print(f"Warning: Could not read frontend .env: {e}")
            
        if not self.base_url:
            self.base_url = "http://localhost:8001/api"
            
        print(f"Testing backend at: {self.base_url}")
        
        self.tests_run = 0
        self.tests_passed = 0
        self.job_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {}
        
        # Don't set Content-Type for multipart/form-data (files)
        if not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=data)
                else:
                    response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {response_data}")
                    return True, response_data
                except:
                    print(f"   Response: {response.text[:200]}...")
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health(self):
        """Test health endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "/health",
            200
        )
        if success and response.get('status') == 'ok':
            print("   ✓ Health status is 'ok'")
            return True
        elif success:
            print(f"   ⚠️ Health status is '{response.get('status')}', expected 'ok'")
        return False

    def test_list_jobs_empty(self):
        """Test listing jobs (should be empty initially)"""
        success, response = self.run_test(
            "List Jobs (Empty)",
            "GET",
            "/jobs",
            200
        )
        if success and 'items' in response:
            items = response['items']
            print(f"   ✓ Found {len(items)} jobs")
            return True
        return False

    def create_test_csv(self):
        """Create a test CSV file with CPF/CNPJ data"""
        test_data = [
            ['documento'],
            ['12345678901'],  # CPF format (11 digits)
            ['12345678000195'],  # CNPJ format (14 digits)
            ['invalid'],  # Invalid format
        ]
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        writer = csv.writer(temp_file)
        writer.writerows(test_data)
        temp_file.close()
        return temp_file.name

    def test_create_job(self):
        """Test creating a job with CSV upload"""
        csv_path = self.create_test_csv()
        
        try:
            with open(csv_path, 'rb') as f:
                files = {'file': ('test.csv', f, 'text/csv')}
                data = {'type': 'auto'}
                
                success, response = self.run_test(
                    "Create Job",
                    "POST",
                    "/jobs",
                    200,  # FastAPI returns 200 for successful POST, not 201
                    data=data,
                    files=files
                )
                
                if success and 'id' in response:
                    self.job_id = response['id']
                    print(f"   ✓ Job created with ID: {self.job_id}")
                    print(f"   ✓ Status: {response.get('status')}")
                    return True
                    
        except Exception as e:
            print(f"   ❌ Error creating test CSV or uploading: {e}")
        finally:
            try:
                os.unlink(csv_path)
            except:
                pass
                
        return False

    def test_get_job(self):
        """Test getting a specific job"""
        if not self.job_id:
            print("   ⚠️ No job ID available, skipping test")
            return False
            
        success, response = self.run_test(
            "Get Job",
            "GET",
            f"/jobs/{self.job_id}",
            200
        )
        
        if success and response.get('id') == self.job_id:
            print(f"   ✓ Job retrieved successfully")
            print(f"   ✓ Status: {response.get('status')}")
            print(f"   ✓ Total: {response.get('total')}")
            return True
        return False

    def test_job_results(self):
        """Test getting job results in CSV and JSON format"""
        if not self.job_id:
            print("   ⚠️ No job ID available, skipping test")
            return False
            
        # Wait a bit for job processing
        print("   ⏳ Waiting for job processing...")
        time.sleep(3)
        
        # Test CSV format
        csv_success, _ = self.run_test(
            "Get Results (CSV)",
            "GET",
            f"/jobs/{self.job_id}/results",
            200,
            params={'format': 'csv'}
        )
        
        # Test JSON format  
        json_success, json_response = self.run_test(
            "Get Results (JSON)",
            "GET",
            f"/jobs/{self.job_id}/results",
            200,
            params={'format': 'json'}
        )
        
        if json_success and isinstance(json_response, list):
            print(f"   ✓ JSON results contain {len(json_response)} records")
            
        return csv_success and json_success

    def test_list_jobs_with_data(self):
        """Test listing jobs after creating one"""
        success, response = self.run_test(
            "List Jobs (With Data)",
            "GET",
            "/jobs",
            200
        )
        if success and 'items' in response:
            items = response['items']
            print(f"   ✓ Found {len(items)} jobs")
            if items and self.job_id:
                found_job = any(job['id'] == self.job_id for job in items)
                if found_job:
                    print(f"   ✓ Created job found in list")
                else:
                    print(f"   ⚠️ Created job not found in list")
            return True
        return False

def main():
    print("🚀 Starting saude-fetch API tests...")
    tester = SaudeFetchAPITester()
    
    # Run all tests
    tests = [
        tester.test_health,
        tester.test_list_jobs_empty,
        tester.test_create_job,
        tester.test_get_job,
        tester.test_job_results,
        tester.test_list_jobs_with_data,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            tester.tests_run += 1
    
    # Print results
    print(f"\n📊 Backend API Tests Summary:")
    print(f"   Tests run: {tester.tests_run}")
    print(f"   Tests passed: {tester.tests_passed}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("✅ All backend tests passed!")
        return 0
    else:
        print("❌ Some backend tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())