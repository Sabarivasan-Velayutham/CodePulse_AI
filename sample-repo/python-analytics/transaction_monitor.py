"""
Transaction Monitoring Module
Real-time monitoring of transaction patterns
"""

import mysql.connector
from datetime import datetime, timedelta
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransactionMonitor:
    """
    Monitors transactions in real-time
    Connects to database and analyzes patterns
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.alert_threshold = 0.80
    
    def get_customer_transactions(self, customer_id: str, days: int = 90) -> List[Dict]:
        """
        Get transaction history for customer
        """
        query = """
        SELECT 
            transaction_id,
            customer_id,
            account_id,
            amount,
            fee,
            type,
            status,
            processed_at,
            device_id,
            ip_address,
            geo_location
        FROM transactions
        WHERE customer_id = %s
        AND processed_at > DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY processed_at DESC
        """
        
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(query, (customer_id, days))
            transactions = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Retrieved {len(transactions)} transactions for customer {customer_id}")
            return transactions
            
        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return []
    
    def get_daily_transactions(self, date: datetime) -> List[Dict]:
        """Get all transactions for a specific day"""
        query = """
        SELECT *
        FROM transactions
        WHERE DATE(processed_at) = DATE(%s)
        """
        
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(query, (date,))
            transactions = cursor.fetchall()
            cursor.close()
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error fetching daily transactions: {e}")
            return []
    
    def get_fraud_alerts(self, customer_id: str) -> List[Dict]:
        """Get fraud alerts for customer"""
        query = """
        SELECT *
        FROM fraud_alerts
        WHERE customer_id = %s
        ORDER BY alert_timestamp DESC
        LIMIT 100
        """
        
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(query, (customer_id,))
            alerts = cursor.fetchall()
            cursor.close()
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error fetching fraud alerts: {e}")
            return []
    
    def monitor_real_time(self):
        """
        Real-time monitoring (would run as background service)
        """
        logger.info("Starting real-time transaction monitoring...")
        
        # Get recent transactions (last 5 minutes)
        query = """
        SELECT *
        FROM transactions
        WHERE processed_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
        AND requires_manual_review = TRUE
        """
        
        try:
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(query)
            pending_review = cursor.fetchall()
            cursor.close()
            
            if pending_review:
                logger.warning(f"Found {len(pending_review)} transactions requiring manual review")
                
                for txn in pending_review:
                    logger.info(f"Transaction {txn['transaction_id']} - Amount: ${txn['amount']}")
            
        except Exception as e:
            logger.error(f"Error in real-time monitoring: {e}")