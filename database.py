import sqlite3
from datetime import datetime
import os
from typing import List, Dict, Optional

class Database:
    def __init__(self):
        # Get the directory containing this file
        basedir = os.path.abspath(os.path.dirname(__file__))
        self.db_path = os.path.join(basedir, 'instance', 'resqlink.db')
        
        # Create instance directory if it doesn't exist
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
        
        # Initialize the database
        self.init_db()

    def get_db_connection(self):
        """Create a database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize the database with required tables"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Create help_requests table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS help_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    location TEXT NOT NULL,
                    district TEXT NOT NULL,
                    state TEXT NOT NULL,
                    pincode TEXT,
                    latitude TEXT,
                    longitude TEXT,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    people_affected INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Add a new table for region alerts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS region_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    district TEXT NOT NULL,
                    state TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')

            # Add a table for emergency contacts
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emergency_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    district TEXT NOT NULL,
                    state TEXT NOT NULL,
                    category TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            conn.commit()
            print("Database initialized successfully")

        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
            raise
        finally:
            conn.close()

    def add_request(self, request_data: Dict) -> int:
        """
        Add a new help request to the database
        
        Args:
            request_data: Dictionary containing request details
            
        Returns:
            The ID of the newly inserted request
            
        Raises:
            ValueError: If required fields are missing
            sqlite3.Error: If database operation fails
        """
        required_fields = ['name', 'contact', 'location', 'category', 'description']
        
        # Validate required fields
        for field in required_fields:
            if not request_data.get(field):
                raise ValueError(f"Missing required field: {field}")

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            query = '''
                INSERT INTO help_requests 
                (name, contact, location, category, description, people_affected, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            cursor.execute(query, (
                request_data['name'],
                request_data['contact'],
                request_data['location'],
                request_data['category'],
                request_data['description'],
                request_data.get('people_affected', 1),
                request_data.get('status', 'pending'),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            request_id = cursor.lastrowid
            return request_id

        except sqlite3.Error as e:
            print(f"Error adding request: {e}")
            raise
        finally:
            conn.close()

    def get_all_requests(self, category: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        """
        Retrieve all help requests from the database
        
        Args:
            category: Optional category filter
            status: Optional status filter
            
        Returns:
            List of dictionaries containing request details
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM help_requests"
            params = []

            # Add filters if provided
            if category or status:
                query += " WHERE"
                if category:
                    query += " category = ?"
                    params.append(category)
                if status:
                    if category:
                        query += " AND"
                    query += " status = ?"
                    params.append(status)

            query += " ORDER BY timestamp DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert rows to list of dictionaries
            requests = []
            for row in rows:
                requests.append({
                    'id': row['id'],
                    'name': row['name'],
                    'contact': row['contact'],
                    'location': row['location'],
                    'category': row['category'],
                    'description': row['description'],
                    'people_affected': row['people_affected'],
                    'status': row['status'],
                    'timestamp': row['timestamp']
                })

            return requests

        except sqlite3.Error as e:
            print(f"Error retrieving requests: {e}")
            raise
        finally:
            conn.close()

    def get_request_by_id(self, request_id: int) -> Optional[Dict]:
        """
        Retrieve a specific help request by ID
        
        Args:
            request_id: The ID of the request to retrieve
            
        Returns:
            Dictionary containing request details or None if not found
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM help_requests WHERE id = ?", (request_id,))
            row = cursor.fetchone()

            if row:
                return {
                    'id': row['id'],
                    'name': row['name'],
                    'contact': row['contact'],
                    'location': row['location'],
                    'category': row['category'],
                    'description': row['description'],
                    'people_affected': row['people_affected'],
                    'status': row['status'],
                    'timestamp': row['timestamp']
                }
            return None

        except sqlite3.Error as e:
            print(f"Error retrieving request: {e}")
            raise
        finally:
            conn.close()

    def update_request_status(self, request_id: int, status: str) -> bool:
        """
        Update the status of a help request
        
        Args:
            request_id: The ID of the request to update
            status: The new status value
            
        Returns:
            Boolean indicating success of the update
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE help_requests SET status = ? WHERE id = ?",
                (status, request_id)
            )
            
            conn.commit()
            return cursor.rowcount > 0

        except sqlite3.Error as e:
            print(f"Error updating request status: {e}")
            raise
        finally:
            conn.close()

    def cleanup_old_requests(self, days: int):
        """
        Remove requests older than specified days
        
        Args:
            days: Number of days after which to remove requests
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM help_requests WHERE datetime(timestamp) < datetime('now', ?)",
                (f'-{days} days',)
            )
            
            conn.commit()

        except sqlite3.Error as e:
            print(f"Error cleaning up old requests: {e}")
            raise
        finally:
            conn.close()

    def add_emergency_contact(self, contact_data: Dict) -> int:
        """Add emergency contact to database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = '''
                INSERT INTO emergency_contacts 
                (name, phone, district, state, category)
                VALUES (?, ?, ?, ?, ?)
            '''
            
            cursor.execute(query, (
                contact_data['name'],
                contact_data['phone'],
                contact_data['district'],
                contact_data['state'],
                contact_data['category']
            ))
            
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_contacts_by_region(self, district: str, state: str) -> List[Dict]:
        """Get emergency contacts for a specific region"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM emergency_contacts 
                WHERE district = ? AND state = ? AND is_active = 1
            ''', (district, state))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_affected_regions(self) -> List[Dict]:
        """Get regions with active help requests"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT district, state, COUNT(*) as request_count,
                       GROUP_CONCAT(DISTINCT category) as categories
                FROM help_requests
                WHERE status = 'pending'
                GROUP BY district, state
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def add_region_alert(self, alert_data: Dict) -> int:
        """Add new region alert"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = '''
                INSERT INTO region_alerts 
                (district, state, alert_type, severity, description)
                VALUES (?, ?, ?, ?, ?)
            '''
            
            cursor.execute(query, (
                alert_data['district'],
                alert_data['state'],
                alert_data['alert_type'],
                alert_data['severity'],
                alert_data['description']
            ))
            
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

# Create a global database instance
db = Database()
