"""
Fraud Analysis Module
Analyzes transaction patterns for fraud detection
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json

from transaction_monitor import TransactionMonitor
from reporting import ReportGenerator


class FraudAnalyzer:
    """
    Main fraud analysis engine
    Uses statistical analysis and pattern detection
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.monitor = TransactionMonitor(db_connection)
        self.report_generator = ReportGenerator()
        self.risk_threshold = 0.85
        
    def analyze_customer_behavior(self, customer_id: str) -> Dict:
        """
        Analyze customer transaction behavior
        Returns risk score and anomalies
        """
        # Get transaction history
        transactions = self.monitor.get_customer_transactions(
            customer_id, 
            days=90
        )
        
        if len(transactions) == 0:
            return {
                "risk_score": 0.5,
                "anomalies": [],
                "status": "insufficient_data"
            }
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(transactions)
        
        # Calculate statistics
        stats = self._calculate_statistics(df)
        
        # Detect anomalies
        anomalies = self._detect_anomalies(df, stats)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(stats, anomalies)
        
        return {
            "risk_score": risk_score,
            "anomalies": anomalies,
            "statistics": stats,
            "status": "analyzed"
        }
    
    def _calculate_statistics(self, df: pd.DataFrame) -> Dict:
        """Calculate transaction statistics"""
        return {
            "mean_amount": df['amount'].mean(),
            "median_amount": df['amount'].median(),
            "std_amount": df['amount'].std(),
            "max_amount": df['amount'].max(),
            "min_amount": df['amount'].min(),
            "total_transactions": len(df),
            "avg_daily_transactions": len(df) / 90,
            "unique_locations": df['geo_location'].nunique(),
            "unique_devices": df['device_id'].nunique()
        }
    
    def _detect_anomalies(self, df: pd.DataFrame, stats: Dict) -> List[Dict]:
        """Detect anomalous transactions"""
        anomalies = []
        
        # Anomaly 1: Amount significantly higher than average
        threshold = stats['mean_amount'] + (3 * stats['std_amount'])
        high_amount = df[df['amount'] > threshold]
        
        for idx, row in high_amount.iterrows():
            anomalies.append({
                "type": "high_amount",
                "transaction_id": row['transaction_id'],
                "amount": row['amount'],
                "expected_max": threshold,
                "severity": "high"
            })
        
        # Anomaly 2: Rapid succession of transactions
        df['time_diff'] = df['processed_at'].diff().dt.total_seconds() / 60
        rapid_transactions = df[df['time_diff'] < 5]  # Less than 5 minutes
        
        if len(rapid_transactions) > 0:
            anomalies.append({
                "type": "rapid_succession",
                "count": len(rapid_transactions),
                "min_interval_minutes": df['time_diff'].min(),
                "severity": "medium"
            })
        
        # Anomaly 3: New location
        if stats['unique_locations'] > 5:
            anomalies.append({
                "type": "multiple_locations",
                "count": stats['unique_locations'],
                "severity": "medium"
            })
        
        # Anomaly 4: New device with high transaction
        for idx, row in df.iterrows():
            if row['amount'] > stats['mean_amount'] * 5:
                # Check if device is new
                device_transactions = df[df['device_id'] == row['device_id']]
                if len(device_transactions) == 1:
                    anomalies.append({
                        "type": "new_device_high_amount",
                        "transaction_id": row['transaction_id'],
                        "device_id": row['device_id'],
                        "amount": row['amount'],
                        "severity": "high"
                    })
        
        return anomalies
    
    def _calculate_risk_score(self, stats: Dict, anomalies: List[Dict]) -> float:
        """Calculate overall risk score (0-1)"""
        score = 0.0
        
        # Base score from statistics
        if stats['total_transactions'] < 5:
            score += 0.2  # New customer risk
        
        if stats['avg_daily_transactions'] > 5:
            score += 0.1  # High frequency
        
        if stats['unique_devices'] > 3:
            score += 0.15  # Multiple devices
        
        # Add score from anomalies
        for anomaly in anomalies:
            if anomaly['severity'] == 'high':
                score += 0.25
            elif anomaly['severity'] == 'medium':
                score += 0.15
            else:
                score += 0.05
        
        return min(score, 1.0)  # Cap at 1.0
    
    def generate_daily_report(self, date: datetime) -> Dict:
        """Generate daily fraud analysis report"""
        # Get all transactions for the day
        transactions = self.monitor.get_daily_transactions(date)
        
        # Analyze each transaction
        high_risk_transactions = []
        total_risk_score = 0.0
        
        for txn in transactions:
            analysis = self.analyze_customer_behavior(txn['customer_id'])
            
            if analysis['risk_score'] > self.risk_threshold:
                high_risk_transactions.append({
                    "transaction_id": txn['transaction_id'],
                    "customer_id": txn['customer_id'],
                    "amount": txn['amount'],
                    "risk_score": analysis['risk_score'],
                    "anomalies": analysis['anomalies']
                })
            
            total_risk_score += analysis['risk_score']
        
        # Generate report
        report = {
            "date": date.strftime("%Y-%m-%d"),
            "total_transactions": len(transactions),
            "high_risk_count": len(high_risk_transactions),
            "average_risk_score": total_risk_score / len(transactions) if transactions else 0,
            "high_risk_transactions": high_risk_transactions
        }
        
        # Save report
        self.report_generator.save_fraud_report(report)
        
        return report
    
    def get_customer_risk_profile(self, customer_id: str) -> Dict:
        """Get comprehensive risk profile for customer"""
        analysis = self.analyze_customer_behavior(customer_id)
        
        # Get historical fraud alerts
        alerts = self.monitor.get_fraud_alerts(customer_id)
        
        # Determine risk level
        if analysis['risk_score'] > 0.85:
            risk_level = "CRITICAL"
        elif analysis['risk_score'] > 0.65:
            risk_level = "HIGH"
        elif analysis['risk_score'] > 0.45:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "customer_id": customer_id,
            "risk_level": risk_level,
            "risk_score": analysis['risk_score'],
            "anomalies": analysis['anomalies'],
            "fraud_alerts_count": len(alerts),
            "last_analyzed": datetime.now().isoformat()
        }