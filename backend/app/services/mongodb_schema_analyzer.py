"""
MongoDB Schema Analyzer
Parses MongoDB schema changes and extracts collection relationships
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CollectionField:
    """Represents a MongoDB collection field"""
    name: str
    data_type: str  # inferred from sample data
    indexed: bool = False
    required: bool = False


@dataclass
class MongoDBCollection:
    """Represents a MongoDB collection"""
    name: str
    fields: List[CollectionField] = None
    indexes: List[Dict] = None


@dataclass
class MongoSchemaChange:
    """Represents a MongoDB schema change"""
    change_type: str  # CREATE_COLLECTION, DROP_COLLECTION, CREATE_INDEX, DROP_INDEX, MODIFY_COLLECTION
    collection_name: str
    index_name: Optional[str] = None
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    operation_statement: Optional[str] = None  # MongoDB operation (e.g., "db.collection.createIndex(...)")


class MongoDBSchemaAnalyzer:
    """Analyzes MongoDB schema and schema changes"""
    
    def __init__(self):
        self.collections: Dict[str, MongoDBCollection] = {}
    
    def parse_schema_change(self, operation_statement: str) -> Optional[MongoSchemaChange]:
        """
        Parse a MongoDB schema change operation statement
        
        Args:
            operation_statement: MongoDB operation (e.g., "CREATE COLLECTION transactions", 
                                  "db.transactions.createIndex(...)", etc.)
        
        Returns:
            MongoSchemaChange object or None
        """
        if not operation_statement:
            return None
        
        op_upper = operation_statement.upper().strip()
        
        # CREATE COLLECTION collection_name
        create_coll_match = re.match(
            r'CREATE\s+COLLECTION\s+(\w+)',
            op_upper,
            re.IGNORECASE
        )
        if create_coll_match:
            return MongoSchemaChange(
                change_type="CREATE_COLLECTION",
                collection_name=create_coll_match.group(1).upper(),
                operation_statement=operation_statement
            )
        
        # DROP COLLECTION collection_name
        drop_coll_match = re.match(
            r'DROP\s+COLLECTION\s+(\w+)',
            op_upper,
            re.IGNORECASE
        )
        if drop_coll_match:
            return MongoSchemaChange(
                change_type="DROP_COLLECTION",
                collection_name=drop_coll_match.group(1).upper(),
                operation_statement=operation_statement
            )
        
        # CREATE INDEX on collection
        # Pattern: db.collection.createIndex({field: 1})
        create_index_match = re.search(
            r'(\w+)\.createIndex\s*\([^)]*\)',
            operation_statement,
            re.IGNORECASE
        )
        if create_index_match:
            collection_name = create_index_match.group(1)
            # Try to extract index name or field
            index_field_match = re.search(r'\{["\']?(\w+)["\']?\s*:', operation_statement, re.IGNORECASE)
            field_name = index_field_match.group(1) if index_field_match else None
            
            return MongoSchemaChange(
                change_type="CREATE_INDEX",
                collection_name=collection_name.upper(),
                field_name=field_name.upper() if field_name else None,
                operation_statement=operation_statement
            )
        
        # DROP INDEX
        # Pattern: db.collection.dropIndex("index_name")
        drop_index_match = re.search(
            r'(\w+)\.dropIndex\s*\([^)]+\)',
            operation_statement,
            re.IGNORECASE
        )
        if drop_index_match:
            collection_name = drop_index_match.group(1)
            # Try to extract index name
            index_name_match = re.search(r'["\']([^"\']+)["\']', operation_statement)
            index_name = index_name_match.group(1) if index_name_match else None
            
            return MongoSchemaChange(
                change_type="DROP_INDEX",
                collection_name=collection_name.upper(),
                index_name=index_name.upper() if index_name else None,
                operation_statement=operation_statement
            )
        
        # MODIFY COLLECTION (generic)
        modify_coll_match = re.match(
            r'MODIFY\s+COLLECTION\s+(\w+)',
            op_upper,
            re.IGNORECASE
        )
        if modify_coll_match:
            return MongoSchemaChange(
                change_type="MODIFY_COLLECTION",
                collection_name=modify_coll_match.group(1).upper(),
                operation_statement=operation_statement
            )
        
        # If we only have collection name, return generic change
        # Try to extract collection name from various patterns
        coll_name_match = re.search(r'\b(\w+)\b', operation_statement)
        if coll_name_match:
            # Common collection names in banking
            common_collections = ["transactions", "accounts", "customers", "fraud_alerts", "transfers"]
            potential_name = coll_name_match.group(1).lower()
            if potential_name in common_collections or len(potential_name) > 3:
                return MongoSchemaChange(
                    change_type="MODIFY_COLLECTION",
                    collection_name=potential_name.upper(),
                    operation_statement=operation_statement
                )
        
        return None
    
    def get_collection_relationships(self, collection_name: str, db_client=None) -> Dict:
        """
        Get all relationships for a collection (references, embedded documents, etc.)
        
        Args:
            collection_name: Name of the collection
            db_client: Optional MongoDB client to query actual relationships
        
        Returns:
            Dictionary with forward and reverse relationships
        """
        relationships = {"forward": [], "reverse": []}
        
        # If we have a database client, query actual relationships
        if db_client:
            try:
                db = db_client.get_database()
                collection = db[collection_name]
                
                # Get sample documents to infer relationships
                sample_doc = collection.find_one()
                if sample_doc:
                    # Look for foreign key-like fields (e.g., customer_id, account_id)
                    for key, value in sample_doc.items():
                        if key.endswith("_id") and key != "_id":
                            # This might reference another collection
                            referenced_collection = key.replace("_id", "").replace("Id", "")
                            relationships["forward"].append({
                                "type": "REFERENCE",
                                "target_collection": referenced_collection,
                                "field": key
                            })
                
                # Find collections that might reference this one
                all_collections = db.list_collection_names()
                for other_coll_name in all_collections:
                    if other_coll_name == collection_name:
                        continue
                    
                    other_coll = db[other_coll_name]
                    sample_other = other_coll.find_one()
                    if sample_other:
                        # Check if this collection is referenced
                        ref_field = f"{collection_name.lower().rstrip('s')}_id"
                        if ref_field in sample_other:
                            relationships["reverse"].append({
                                "type": "REFERENCED_BY",
                                "source_collection": other_coll_name,
                                "field": ref_field
                            })
            
            except Exception as e:
                print(f"⚠️ Could not query MongoDB for relationships: {e}")
        
        return relationships

