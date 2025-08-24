import sqlitecloud
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Database:
    def __init__(self, connection_string='sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/financial_system.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k'):
        self.connection_string = connection_string
        self.init_db()
    
    def get_connection(self):
        conn = sqlitecloud.connect(self.connection_string)
        # SQLite Cloud doesn't support sqlite3.Row directly
        # We'll work with tuples and column names instead
        return conn
    
    def init_db(self):
        """Initialize database with all required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1,
                trial_start_date TEXT DEFAULT CURRENT_TIMESTAMP,
                trial_end_date TEXT,
                subscription_plan TEXT DEFAULT 'trial',
                subscription_status TEXT DEFAULT 'trial',
                subscription_end_date TEXT
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                category TEXT,
                date TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_recurring INTEGER DEFAULT 0,
                recurrence_type TEXT,
                account_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')
        
        # Accounts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                amount REAL DEFAULT 0,
                due_date TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Financial goals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                target_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_completed INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        try:
            conn.commit()
        except Exception as e:
            # SQLite Cloud auto-commit behavior - this is expected
            pass
        conn.close()
        logging.info("Database initialized successfully")

# Global database instance
db_manager = Database()

class User:
    def __init__(self, id=None, username=None, email=None, password_hash=None, 
                 full_name=None, phone=None, created_at=None, active=None,
                 trial_start_date=None, trial_end_date=None, subscription_plan=None,
                 subscription_status=None, subscription_end_date=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.phone = phone
        self.created_at = self._parse_datetime(created_at)
        self.active = bool(active) if active is not None else True
        self.trial_start_date = self._parse_datetime(trial_start_date)
        self.trial_end_date = self._parse_datetime(trial_end_date)
        self.subscription_plan = subscription_plan or 'trial'
        self.subscription_status = subscription_status or 'trial'
        self.subscription_end_date = self._parse_datetime(subscription_end_date)
    
    def _parse_datetime(self, date_str):
        """Convert string dates to datetime objects"""
        if date_str is None:
            return None
        if isinstance(date_str, datetime):
            return date_str
        if isinstance(date_str, str):
            try:
                # Try parsing ISO format
                return datetime.fromisoformat(date_str.replace('Z', '+00:00').replace('+00:00', ''))
            except ValueError:
                try:
                    # Try parsing with timezone info removed
                    return datetime.fromisoformat(date_str.split('+')[0].split('Z')[0])
                except ValueError:
                    return None
        return None
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)
    
    def is_authenticated(self):
        return True
    
    def is_active(self):
        return self.active
    
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def is_trial_expired(self):
        if not self.trial_end_date:
            return False
        if isinstance(self.trial_end_date, datetime):
            return datetime.utcnow() > self.trial_end_date
        # If it's still a string, try to parse it
        trial_end = self._parse_datetime(self.trial_end_date)
        if trial_end:
            return datetime.utcnow() > trial_end
        return False
    
    def is_subscription_active(self):
        if self.subscription_status == 'trial':
            return not self.is_trial_expired()
        if self.subscription_status == 'active' and self.subscription_end_date:
            if isinstance(self.subscription_end_date, datetime):
                return datetime.utcnow() <= self.subscription_end_date
            # If it's still a string, try to parse it
            sub_end = self._parse_datetime(self.subscription_end_date)
            if sub_end:
                return datetime.utcnow() <= sub_end
        return False
    
    def get_plan_features(self):
        features = {
            'trial': {
                'name': 'Teste Grátis',
                'transactions_limit': 10,
                'reports': False,
                'automation': False,
                'multi_user': False
            },
            'mei': {
                'name': 'Plano MEI',
                'transactions_limit': 100,
                'reports': True,
                'automation': False,
                'multi_user': False
            },
            'professional': {
                'name': 'Plano Profissional',
                'transactions_limit': 500,
                'reports': True,
                'automation': True,
                'multi_user': False
            },
            'enterprise': {
                'name': 'Plano Empresarial',
                'transactions_limit': -1,  # unlimited
                'reports': True,
                'automation': True,
                'multi_user': True
            }
        }
        return features.get(self.subscription_plan, features['trial'])
    
    @staticmethod
    def create(username, email, password, full_name, phone=None):
        """Create a new user"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Set trial end date (7 days from now)
        trial_end = (datetime.utcnow() + timedelta(days=7)).isoformat()
        
        password_hash = generate_password_hash(password)
        
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name, phone, trial_end_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, full_name, phone, trial_end))
        
        user_id = cursor.lastrowid
        try:
            conn.commit()
        except Exception as e:
            # SQLite Cloud auto-commit behavior - this is expected
            pass
        conn.close()
        
        return User.get_by_id(user_id)
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, email, password_hash, full_name, phone, created_at, active, trial_start_date, trial_end_date, subscription_plan, subscription_status, subscription_end_date FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row[0], username=row[1], email=row[2], password_hash=row[3],
                full_name=row[4], phone=row[5], created_at=row[6], active=row[7],
                trial_start_date=row[8], trial_end_date=row[9], subscription_plan=row[10],
                subscription_status=row[11], subscription_end_date=row[12]
            )
        return None
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, email, password_hash, full_name, phone, created_at, active, trial_start_date, trial_end_date, subscription_plan, subscription_status, subscription_end_date FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row[0], username=row[1], email=row[2], password_hash=row[3],
                full_name=row[4], phone=row[5], created_at=row[6], active=row[7],
                trial_start_date=row[8], trial_end_date=row[9], subscription_plan=row[10],
                subscription_status=row[11], subscription_end_date=row[12]
            )
        return None
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, email, password_hash, full_name, phone, created_at, active, trial_start_date, trial_end_date, subscription_plan, subscription_status, subscription_end_date FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return User(
                id=row[0], username=row[1], email=row[2], password_hash=row[3],
                full_name=row[4], phone=row[5], created_at=row[6], active=row[7],
                trial_start_date=row[8], trial_end_date=row[9], subscription_plan=row[10],
                subscription_status=row[11], subscription_end_date=row[12]
            )
        return None

class Transaction:
    def __init__(self, id=None, user_id=None, description=None, amount=None,
                 transaction_type=None, category=None, date=None, created_at=None,
                 is_recurring=None, recurrence_type=None, account_id=None):
        self.id = id
        self.user_id = user_id
        self.description = description
        self.amount = float(amount) if amount else 0.0
        self.transaction_type = transaction_type
        self.category = category
        self.date = self._parse_datetime(date)
        self.created_at = self._parse_datetime(created_at)
        self.is_recurring = bool(is_recurring) if is_recurring else False
        self.recurrence_type = recurrence_type
        self.account_id = account_id
    
    def _parse_datetime(self, date_str):
        """Convert string dates to datetime objects"""
        if date_str is None:
            return None
        if isinstance(date_str, datetime):
            return date_str
        if isinstance(date_str, str):
            try:
                # Try parsing ISO format
                return datetime.fromisoformat(date_str.replace('Z', '+00:00').replace('+00:00', ''))
            except ValueError:
                try:
                    # Try parsing with timezone info removed
                    return datetime.fromisoformat(date_str.split('+')[0].split('Z')[0])
                except ValueError:
                    return None
        return None
    
    def save(self):
        """Save transaction to database"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing
            cursor.execute('''
                UPDATE transactions 
                SET description=?, amount=?, transaction_type=?, category=?, 
                    date=?, is_recurring=?, recurrence_type=?, account_id=?
                WHERE id=?
            ''', (self.description, self.amount, self.transaction_type, self.category,
                  self.date, self.is_recurring, self.recurrence_type, self.account_id, self.id))
        else:
            # Create new
            cursor.execute('''
                INSERT INTO transactions (user_id, description, amount, transaction_type, 
                                        category, date, is_recurring, recurrence_type, account_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.user_id, self.description, self.amount, self.transaction_type,
                  self.category, self.date, self.is_recurring, self.recurrence_type, self.account_id))
            self.id = cursor.lastrowid
        
        try:
            conn.commit()
        except Exception as e:
            # SQLite Cloud auto-commit behavior - this is expected
            pass
        conn.close()
        return self
    
    @staticmethod
    def get_by_user_id(user_id, limit=None, order_by='date DESC'):
        """Get transactions by user ID"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        query = f'SELECT id, user_id, description, amount, transaction_type, category, date, created_at, is_recurring, recurrence_type, account_id FROM transactions WHERE user_id = ? ORDER BY {order_by}'
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [Transaction(
            id=row[0], user_id=row[1], description=row[2], amount=row[3],
            transaction_type=row[4], category=row[5], date=row[6], created_at=row[7],
            is_recurring=row[8], recurrence_type=row[9], account_id=row[10]
        ) for row in rows]
    
    @staticmethod
    def count_by_user_id(user_id):
        """Count transactions by user ID"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    @staticmethod
    def get_monthly_summary(user_id, month, year):
        """Get monthly income and expenses summary"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get monthly income
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) FROM transactions 
            WHERE user_id = ? AND transaction_type = 'income' 
            AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
        ''', (user_id, f'{month:02d}', str(year)))
        
        income_result = cursor.fetchone()
        income = income_result[0] if income_result else 0
        
        # Get monthly expenses
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) FROM transactions 
            WHERE user_id = ? AND transaction_type = 'expense' 
            AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
        ''', (user_id, f'{month:02d}', str(year)))
        
        expenses_result = cursor.fetchone()
        expenses = expenses_result[0] if expenses_result else 0
        conn.close()
        
        return float(income), float(expenses)

class Account:
    def __init__(self, id=None, user_id=None, name=None, account_type=None,
                 amount=None, due_date=None, status=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.account_type = account_type
        self.amount = float(amount) if amount else 0.0
        self.due_date = self._parse_datetime(due_date)
        self.status = status or 'pending'
        self.created_at = self._parse_datetime(created_at)
    
    def _parse_datetime(self, date_str):
        """Convert string dates to datetime objects"""
        if date_str is None:
            return None
        if isinstance(date_str, datetime):
            return date_str
        if isinstance(date_str, str):
            try:
                # Try parsing ISO format
                return datetime.fromisoformat(date_str.replace('Z', '+00:00').replace('+00:00', ''))
            except ValueError:
                try:
                    # Try parsing with timezone info removed
                    return datetime.fromisoformat(date_str.split('+')[0].split('Z')[0])
                except ValueError:
                    return None
        return None
    
    def save(self):
        """Save account to database"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing
            cursor.execute('''
                UPDATE accounts 
                SET name=?, account_type=?, amount=?, due_date=?, status=?
                WHERE id=?
            ''', (self.name, self.account_type, self.amount, self.due_date, self.status, self.id))
        else:
            # Create new
            cursor.execute('''
                INSERT INTO accounts (user_id, name, account_type, amount, due_date, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.user_id, self.name, self.account_type, self.amount, self.due_date, self.status))
            self.id = cursor.lastrowid
        
        try:
            conn.commit()
        except Exception as e:
            # SQLite Cloud auto-commit behavior - this is expected
            pass
        conn.close()
        return self
    
    @staticmethod
    def get_by_user_id(user_id, account_type=None):
        """Get accounts by user ID and optionally by type"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if account_type:
            cursor.execute('SELECT id, user_id, name, account_type, amount, due_date, status, created_at FROM accounts WHERE user_id = ? AND account_type = ?', 
                          (user_id, account_type))
        else:
            cursor.execute('SELECT id, user_id, name, account_type, amount, due_date, status, created_at FROM accounts WHERE user_id = ?', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [Account(
            id=row[0], user_id=row[1], name=row[2], account_type=row[3],
            amount=row[4], due_date=row[5], status=row[6], created_at=row[7]
        ) for row in rows]
    
    @staticmethod
    def get_by_id(account_id, user_id=None):
        """Get account by ID, optionally filtered by user"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('SELECT id, user_id, name, account_type, amount, due_date, status, created_at FROM accounts WHERE id = ? AND user_id = ?', (account_id, user_id))
        else:
            cursor.execute('SELECT id, user_id, name, account_type, amount, due_date, status, created_at FROM accounts WHERE id = ?', (account_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Account(
                id=row[0], user_id=row[1], name=row[2], account_type=row[3],
                amount=row[4], due_date=row[5], status=row[6], created_at=row[7]
            )
        return None
    
    @staticmethod
    def get_pending_total(user_id, account_type):
        """Get total amount for pending accounts of a specific type"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COALESCE(SUM(amount), 0) FROM accounts 
            WHERE user_id = ? AND account_type = ? AND status = 'pending'
        ''', (user_id, account_type))
        
        result = cursor.fetchone()
        total = result[0] if result else 0
        conn.close()
        
        return float(total)

class FinancialGoal:
    def __init__(self, id=None, user_id=None, title=None, target_amount=None,
                 current_amount=None, target_date=None, created_at=None, is_completed=None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.target_amount = float(target_amount) if target_amount else 0.0
        self.current_amount = float(current_amount) if current_amount else 0.0
        self.target_date = self._parse_datetime(target_date)
        self.created_at = self._parse_datetime(created_at)
        self.is_completed = bool(is_completed) if is_completed else False
    
    def _parse_datetime(self, date_str):
        """Convert string dates to datetime objects"""
        if date_str is None:
            return None
        if isinstance(date_str, datetime):
            return date_str
        if isinstance(date_str, str):
            try:
                # Try parsing ISO format
                return datetime.fromisoformat(date_str.replace('Z', '+00:00').replace('+00:00', ''))
            except ValueError:
                try:
                    # Try parsing with timezone info removed
                    return datetime.fromisoformat(date_str.split('+')[0].split('Z')[0])
                except ValueError:
                    return None
        return None
    
    def get_progress_percentage(self):
        if self.target_amount == 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)
    
    def save(self):
        """Save goal to database"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing
            cursor.execute('''
                UPDATE financial_goals 
                SET title=?, target_amount=?, current_amount=?, target_date=?, is_completed=?
                WHERE id=?
            ''', (self.title, self.target_amount, self.current_amount, 
                  self.target_date, self.is_completed, self.id))
        else:
            # Create new
            cursor.execute('''
                INSERT INTO financial_goals (user_id, title, target_amount, current_amount, target_date, is_completed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.user_id, self.title, self.target_amount, self.current_amount, 
                  self.target_date, self.is_completed))
            self.id = cursor.lastrowid
        
        try:
            conn.commit()
        except Exception as e:
            # SQLite Cloud auto-commit behavior - this is expected
            pass
        conn.close()
        return self
    
    @staticmethod
    def get_by_user_id(user_id, is_completed=None):
        """Get financial goals by user ID"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        if is_completed is not None:
            cursor.execute('SELECT id, user_id, title, target_amount, current_amount, target_date, created_at, is_completed FROM financial_goals WHERE user_id = ? AND is_completed = ? ORDER BY created_at DESC', 
                          (user_id, is_completed))
        else:
            cursor.execute('SELECT id, user_id, title, target_amount, current_amount, target_date, created_at, is_completed FROM financial_goals WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [FinancialGoal(
            id=row[0], user_id=row[1], title=row[2], target_amount=row[3],
            current_amount=row[4], target_date=row[5], created_at=row[6], is_completed=row[7]
        ) for row in rows]
    
    @staticmethod
    def get_by_id(goal_id):
        """Get financial goal by ID"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, user_id, title, target_amount, current_amount, target_date, created_at, is_completed FROM financial_goals WHERE id = ?', (goal_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return FinancialGoal(
                id=row[0], user_id=row[1], title=row[2], target_amount=row[3],
                current_amount=row[4], target_date=row[5], created_at=row[6], is_completed=row[7]
            )
        return None
    
    def delete(self):
        """Delete goal from database"""
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM financial_goals WHERE id = ?', (self.id,))
        try:
            conn.commit()
        except Exception as e:
            # SQLite Cloud auto-commit behavior - this is expected
            pass
        conn.close()
    
    def get_days_remaining(self):
        """Get days remaining to reach target date"""
        if not self.target_date:
            return None
        delta = self.target_date - datetime.now()
        return delta.days
    
    def is_overdue(self):
        """Check if goal is overdue"""
        if not self.target_date:
            return False
        return datetime.now() > self.target_date and not self.is_completed