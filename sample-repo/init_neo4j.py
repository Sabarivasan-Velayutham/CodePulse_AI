#!/usr/bin/env python3
"""
Initialize Neo4j with sample banking app dependencies
This creates the demo dependency graph
"""

from neo4j import GraphDatabase
import sys

class Neo4jInitializer:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Clear all existing data"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("✅ Database cleared")
    
    def create_sample_graph(self):
        """Create sample dependency graph"""
        with self.driver.session() as session:
            # Create Module nodes
            modules = [
                {
                    "name": "PaymentProcessor.java",
                    "type": "class",
                    "path": "/src/payment/",
                    "language": "Java",
                    "criticality": "HIGH",
                    "lines_of_code": 150
                },
                {
                    "name": "FraudDetection.java",
                    "type": "class",
                    "path": "/src/fraud/",
                    "language": "Java",
                    "criticality": "CRITICAL",
                    "lines_of_code": 120
                },
                {
                    "name": "AccountBalance.java",
                    "type": "class",
                    "path": "/src/account/",
                    "language": "Java",
                    "criticality": "HIGH",
                    "lines_of_code": 80
                },
                {
                    "name": "TransactionDAO.java",
                    "type": "class",
                    "path": "/src/database/",
                    "language": "Java",
                    "criticality": "HIGH",
                    "lines_of_code": 100
                },
                {
                    "name": "CustomerDAO.java",
                    "type": "class",
                    "path": "/src/database/",
                    "language": "Java",
                    "criticality": "MEDIUM",
                    "lines_of_code": 90
                },
                {
                    "name": "RegulatoryReporting.java",
                    "type": "class",
                    "path": "/src/reporting/",
                    "language": "Java",
                    "criticality": "CRITICAL",
                    "lines_of_code": 200
                },
                {
                    "name": "NotificationService.java",
                    "type": "class",
                    "path": "/src/notification/",
                    "language": "Java",
                    "criticality": "LOW",
                    "lines_of_code": 50
                }
            ]
            
            for module in modules:
                session.run("""
                    CREATE (m:Module {
                        name: $name,
                        type: $type,
                        path: $path,
                        language: $language,
                        criticality: $criticality,
                        lines_of_code: $lines_of_code
                    })
                """, **module)
            
            print(f"✅ Created {len(modules)} module nodes")
            
            # Create Database Table nodes
            tables = [
                {
                    "name": "TRANSACTIONS",
                    "database": "banking_db",
                    "row_count": 15000000,
                    "columns": "id,account_id,amount,fee,type,status,timestamp"
                },
                {
                    "name": "CUSTOMERS",
                    "database": "banking_db",
                    "row_count": 5000000,
                    "columns": "id,name,email,account_id,created_at"
                },
                {
                    "name": "FRAUD_ALERTS",
                    "database": "banking_db",
                    "row_count": 50000,
                    "columns": "id,transaction_id,reason,timestamp"
                }
            ]
            
            for table in tables:
                session.run("""
                    CREATE (t:DataTable {
                        name: $name,
                        database: $database,
                        row_count: $row_count,
                        columns: $columns
                    })
                """, **table)
            
            print(f"✅ Created {len(tables)} data table nodes")
            
            # Create relationships
            relationships = [
                # PaymentProcessor dependencies
                ("PaymentProcessor.java", "FraudDetection.java", "CALLS", 
                 {"line_number": 35, "method": "checkTransaction"}),
                ("PaymentProcessor.java", "TransactionDAO.java", "CALLS", 
                 {"line_number": 50, "method": "save"}),
                ("PaymentProcessor.java", "AccountBalance.java", "CALLS", 
                 {"line_number": 30, "method": "getBalance"}),
                ("PaymentProcessor.java", "NotificationService.java", "CALLS", 
                 {"line_number": 65, "method": "send"}),
                
                # FraudDetection dependencies
                ("FraudDetection.java", "CustomerDAO.java", "CALLS", 
                 {"line_number": 28, "method": "findById"}),
                
                # AccountBalance dependencies
                ("AccountBalance.java", "TransactionDAO.java", "CALLS", 
                 {"line_number": 22, "method": "findByAccountId"}),
                
                # Database access
                ("TransactionDAO.java", "TRANSACTIONS", "WRITES_TO", 
                 {"operation": "INSERT"}),
                ("TransactionDAO.java", "TRANSACTIONS", "READS_FROM", 
                 {"operation": "SELECT"}),
                ("AccountBalance.java", "TRANSACTIONS", "READS_FROM", 
                 {"operation": "SELECT"}),
                ("CustomerDAO.java", "CUSTOMERS", "READS_FROM", 
                 {"operation": "SELECT"}),
                ("FraudDetection.java", "FRAUD_ALERTS", "WRITES_TO", 
                 {"operation": "INSERT"}),
                
                # Regulatory reporting (indirect dependency)
                ("TRANSACTIONS", "RegulatoryReporting.java", "USED_BY", 
                 {"purpose": "compliance"}),
            ]
            
            for source, target, rel_type, properties in relationships:
                # Determine if source/target is Module or DataTable
                session.run(f"""
                    MATCH (source {{name: $source}})
                    MATCH (target {{name: $target}})
                    CREATE (source)-[r:{rel_type}]->(target)
                    SET r = $properties
                """, source=source, target=target, properties=properties)
            
            print(f"✅ Created {len(relationships)} relationships")
            
            print("\n🎉 Sample dependency graph created successfully!")
            print("\n📊 Graph Statistics:")
            
            # Print statistics
            result = session.run("""
                MATCH (m:Module) 
                RETURN count(m) as module_count
            """)
            module_count = result.single()["module_count"]
            
            result = session.run("""
                MATCH (t:DataTable) 
                RETURN count(t) as table_count
            """)
            table_count = result.single()["table_count"]
            
            result = session.run("""
                MATCH ()-[r]->() 
                RETURN count(r) as relationship_count
            """)
            rel_count = result.single()["relationship_count"]
            
            print(f"   Modules: {module_count}")
            print(f"   Tables: {table_count}")
            print(f"   Relationships: {rel_count}")
            
            print("\n🌐 Open Neo4j Browser: http://localhost:7474")
            print("   Run query: MATCH (n) RETURN n")

def main():
    # Neo4j connection details
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "codeflow123"
    
    print("🚀 Initializing Neo4j with sample data...")
    print(f"   Connecting to: {uri}")
    
    try:
        initializer = Neo4jInitializer(uri, user, password)
        
        # Clear existing data
        response = input("\n⚠️  Clear existing data? (yes/no): ")
        if response.lower() == 'yes':
            initializer.clear_database()
        
        # Create sample graph
        initializer.create_sample_graph()
        
        initializer.close()
        print("\n✅ Initialization complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Neo4j is running:")
        print("   docker-compose up -d neo4j")
        sys.exit(1)

if __name__ == "__main__":
    main()