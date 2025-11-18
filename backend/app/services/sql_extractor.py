"""
SQL Query Extractor
Extracts table and column usage from code files
"""

import re
from typing import Dict, List, Set, Tuple
from pathlib import Path


class SQLExtractor:
    """Extracts SQL queries and table/column references from code"""
    
    def __init__(self):
        # Common SQL keywords
        self.sql_keywords = {
            'SELECT', 'FROM', 'INSERT', 'UPDATE', 'DELETE', 'JOIN',
            'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'WHERE', 'INTO',
            'SET', 'VALUES', 'CREATE', 'ALTER', 'DROP', 'TABLE'
        }
    
    def extract_table_usage(self, file_path: str, file_content: str) -> Dict[str, List[Dict]]:
        """
        Extract all table and column references from a code file
        
        Args:
            file_path: Path to the file
            file_content: Content of the file
        
        Returns:
            Dictionary mapping table_name -> list of usage contexts
        """
        table_usage = {}
        
        # Extract SQL queries (both raw SQL and ORM queries)
        sql_queries = self._extract_sql_queries(file_content)
        
        for query, line_num, context in sql_queries:
            tables = self._extract_tables_from_query(query)
            columns = self._extract_columns_from_query(query, tables)
            
            for table in tables:
                if table not in table_usage:
                    table_usage[table] = []
                
                table_usage[table].append({
                    "line_number": line_num,
                    "query_type": self._get_query_type(query),
                    "columns": columns.get(table, []),
                    "context": context[:100] if context else "",  # First 100 chars
                    "full_query": query[:200]  # First 200 chars
                })
        
        # Also check for ORM model references (JPA, Hibernate, SQLAlchemy)
        orm_tables = self._extract_orm_tables(file_content, file_path)
        for table, line_num in orm_tables:
            if table not in table_usage:
                table_usage[table] = []
            
            table_usage[table].append({
                "line_number": line_num,
                "query_type": "ORM_ENTITY",
                "columns": [],
                "context": "ORM entity/class reference",
                "full_query": ""
            })
        
        # Also check for heuristic class-to-table mappings
        # e.g., AccountBalance -> accounts, TransactionDAO -> transactions
        heuristic_tables = self._extract_heuristic_tables(file_content, file_path)
        for table, line_num in heuristic_tables:
            if table not in table_usage:
                table_usage[table] = []
            
            table_usage[table].append({
                "line_number": line_num,
                "query_type": "HEURISTIC",
                "columns": [],
                "context": "Class/DAO name suggests table usage",
                "full_query": ""
            })
        
        # Also check for MongoDB collection usage patterns
        # e.g., db.transactions.find(), collection.insertOne(), etc.
        mongo_collections = self._extract_mongodb_collections(file_content)
        for collection, line_num, context in mongo_collections:
            if collection not in table_usage:
                table_usage[collection] = []
            
            table_usage[collection].append({
                "line_number": line_num,
                "query_type": "MONGO_OPERATION",
                "columns": [],
                "context": context[:100] if context else "",
                "full_query": ""
            })
        
        return table_usage
    
    def _extract_sql_queries(self, content: str) -> List[Tuple[str, int, str]]:
        """Extract SQL queries from code"""
        queries = []
        lines = content.split('\n')
        
        current_query = ""
        query_start_line = 0
        in_string = False
        string_char = None
        
        for line_num, line in enumerate(lines, 1):
            # Track string boundaries
            i = 0
            while i < len(line):
                char = line[i]
                
                if char in ['"', "'", '`'] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                
                i += 1
            
            # Check if line contains SQL keywords
            line_upper = line.upper()
            has_sql = any(keyword in line_upper for keyword in self.sql_keywords)
            
            if has_sql and not in_string:
                # Check for SQL string patterns
                # Pattern 1: String literal with SQL
                sql_string_pattern = r'["\']([^"\']*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER)[^"\']*)["\']'
                matches = re.finditer(sql_string_pattern, line, re.IGNORECASE)
                
                for match in matches:
                    query = match.group(1)
                    if self._is_sql_query(query):
                        queries.append((query, line_num, line.strip()))
                
                # Pattern 2: Multi-line SQL strings (Java/Python)
                if '"""' in line or "'''" in line or '"""' in line:
                    # Start of multi-line string
                    if current_query == "":
                        query_start_line = line_num
                    current_query += line + "\n"
                elif current_query and ('"""' in line or "'''" in line):
                    # End of multi-line string
                    current_query += line
                    if self._is_sql_query(current_query):
                        queries.append((current_query, query_start_line, current_query[:100]))
                    current_query = ""
                elif current_query:
                    current_query += line + "\n"
        
        return queries
    
    def _is_sql_query(self, text: str) -> bool:
        """Check if text looks like a SQL query"""
        text_upper = text.upper().strip()
        return any(text_upper.startswith(kw) for kw in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'])
    
    def _extract_tables_from_query(self, query: str) -> Set[str]:
        """Extract table names from SQL query"""
        tables = set()
        
        # FROM clause
        from_pattern = r'FROM\s+(?:`)?(\w+)(?:`)?(?:\s|,|$|WHERE|JOIN)'
        from_matches = re.finditer(from_pattern, query, re.IGNORECASE)
        for match in from_matches:
            tables.add(match.group(1))
        
        # JOIN clauses
        join_pattern = r'JOIN\s+(?:`)?(\w+)(?:`)?\s+'
        join_matches = re.finditer(join_pattern, query, re.IGNORECASE)
        for match in join_matches:
            tables.add(match.group(1))
        
        # INSERT INTO
        insert_pattern = r'INSERT\s+INTO\s+(?:`)?(\w+)(?:`)?'
        insert_match = re.search(insert_pattern, query, re.IGNORECASE)
        if insert_match:
            tables.add(insert_match.group(1))
        
        # UPDATE
        update_pattern = r'UPDATE\s+(?:`)?(\w+)(?:`)?'
        update_match = re.search(update_pattern, query, re.IGNORECASE)
        if update_match:
            tables.add(update_match.group(1))
        
        # DELETE FROM
        delete_pattern = r'DELETE\s+FROM\s+(?:`)?(\w+)(?:`)?'
        delete_match = re.search(delete_pattern, query, re.IGNORECASE)
        if delete_match:
            tables.add(delete_match.group(1))
        
        return tables
    
    def _extract_columns_from_query(self, query: str, tables: Set[str]) -> Dict[str, List[str]]:
        """Extract column names from SQL query, grouped by table"""
        columns_by_table = {table: [] for table in tables}
        
        # SELECT columns
        select_pattern = r'SELECT\s+(.*?)\s+FROM'
        select_match = re.search(select_pattern, query, re.IGNORECASE | re.DOTALL)
        if select_match:
            columns_str = select_match.group(1)
            # Split by comma, handle table.column format
            for col in columns_str.split(','):
                col = col.strip()
                # Remove aliases
                if ' AS ' in col.upper():
                    col = col.split(' AS ')[0].strip()
                if ' ' in col and '.' not in col:
                    col = col.split()[0]
                
                # Check if it's table.column format
                if '.' in col:
                    table, column = col.split('.', 1)
                    table = table.strip('`').strip()
                    column = column.strip('`').strip()
                    if table in columns_by_table:
                        if column not in columns_by_table[table]:
                            columns_by_table[table].append(column)
                else:
                    # Column without table prefix - add to all tables (heuristic)
                    col = col.strip('`').strip()
                    if col and col != '*':
                        for table in columns_by_table:
                            if col not in columns_by_table[table]:
                                columns_by_table[table].append(col)
        
        # WHERE clause columns
        where_pattern = r'WHERE\s+(.*?)(?:\s+(?:GROUP|ORDER|LIMIT|JOIN|$))'
        where_match = re.search(where_pattern, query, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            # Extract column names from WHERE clause
            col_pattern = r'(?:`)?(\w+)(?:`)?\s*[=<>!]'
            for match in re.finditer(col_pattern, where_clause):
                col = match.group(1)
                for table in columns_by_table:
                    if col not in columns_by_table[table]:
                        columns_by_table[table].append(col)
        
        # SET clause (UPDATE)
        set_pattern = r'SET\s+(.*?)(?:\s+WHERE|$)'
        set_match = re.search(set_pattern, query, re.IGNORECASE | re.DOTALL)
        if set_match:
            set_clause = set_match.group(1)
            for col_match in re.finditer(r'(?:`)?(\w+)(?:`)?\s*=', set_clause):
                col = col_match.group(1)
                for table in columns_by_table:
                    if col not in columns_by_table[table]:
                        columns_by_table[table].append(col)
        
        return columns_by_table
    
    def _get_query_type(self, query: str) -> str:
        """Determine the type of SQL query"""
        query_upper = query.upper().strip()
        if query_upper.startswith('SELECT'):
            return 'SELECT'
        elif query_upper.startswith('INSERT'):
            return 'INSERT'
        elif query_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif query_upper.startswith('DELETE'):
            return 'DELETE'
        elif query_upper.startswith('CREATE'):
            return 'CREATE'
        elif query_upper.startswith('ALTER'):
            return 'ALTER'
        else:
            return 'UNKNOWN'
    
    def _extract_orm_tables(self, content: str, file_path: str) -> List[Tuple[str, int]]:
        """Extract table names from ORM annotations/classes"""
        tables = []
        lines = content.split('\n')
        
        # Java JPA/Hibernate patterns
        # @Entity(name = "transactions")
        # @Table(name = "transactions")
        entity_pattern = r'@(?:Entity|Table)\s*\([^)]*name\s*=\s*["\'](\w+)["\']'
        table_pattern = r'@Table\s*\([^)]*name\s*=\s*["\'](\w+)["\']'
        
        # Python SQLAlchemy patterns
        # __tablename__ = "transactions"
        sqlalchemy_pattern = r'__tablename__\s*=\s*["\'](\w+)["\']'
        
        for line_num, line in enumerate(lines, 1):
            # Check Java annotations
            for match in re.finditer(entity_pattern, line):
                tables.append((match.group(1), line_num))
            
            for match in re.finditer(table_pattern, line):
                tables.append((match.group(1), line_num))
            
            # Check Python SQLAlchemy
            for match in re.finditer(sqlalchemy_pattern, line):
                tables.append((match.group(1), line_num))
        
        return tables
    
    def _extract_heuristic_tables(self, content: str, file_path: str) -> List[Tuple[str, int]]:
        """Extract table names using heuristics (class names, DAO names, etc.)"""
        tables = []
        lines = content.split('\n')
        
        # Common class-to-table mappings
        # AccountBalance, AccountDAO, AccountService -> accounts
        # TransactionDAO, TransactionService -> transactions
        # CustomerDAO, CustomerService -> customers
        # FraudAlert, FraudDetection -> fraud_alerts
        
        # Pattern: class AccountBalance, AccountDAO, etc.
        # Match: class AccountBalance, class TransactionDAO, etc.
        class_pattern = r'class\s+(\w+)(?:DAO|Service|Manager|Balance|Alert|Detection|Processor)?'
        
        # Common mappings
        name_mappings = {
            'account': 'accounts',
            'transaction': 'transactions',
            'customer': 'customers',
            'fraud': 'fraud_alerts',
            'fraudalert': 'fraud_alerts',
            'transfer': 'transfer_records',
            'balance': 'account_balances'
        }
        
        for line_num, line in enumerate(lines, 1):
            # Check for class names that suggest table usage
            # Match: class AccountBalance, class TransactionDAO, etc.
            class_match = re.search(r'class\s+(\w+)', line, re.IGNORECASE)
            if class_match:
                class_name = class_match.group(1).lower()
                
                # Check if class name contains table-related keywords
                for keyword, table_name in name_mappings.items():
                    if keyword in class_name:
                        tables.append((table_name, line_num))
                        break
        
        # Also check for variable/field names that suggest table usage
        # e.g., accountBalance, transactionDAO, customerService
        # Pattern: private AccountBalance, AccountBalance accountBalance, etc.
        var_pattern = r'(?:private|public|protected|final)?\s+(\w*(?:Account|Transaction|Customer|Fraud|Transfer|Balance)\w*)'
        for line_num, line in enumerate(lines, 1):
            var_matches = re.finditer(var_pattern, line, re.IGNORECASE)
            for match in var_matches:
                var_name = match.group(1).lower() if match.group(1) else ""
                for keyword, table_name in name_mappings.items():
                    if keyword in var_name:
                        tables.append((table_name, line_num))
                        break
        
        return tables
    
    def _extract_mongodb_collections(self, content: str) -> List[Tuple[str, int, str]]:
        """Extract MongoDB collection names from code"""
        collections = []
        lines = content.split('\n')
        
        # MongoDB patterns:
        # db.collection_name.find()
        # db.collection_name.insertOne()
        # db.collection_name.insertMany()
        # db.collection_name.updateOne()
        # db.collection_name.updateMany()
        # db.collection_name.deleteOne()
        # db.collection_name.deleteMany()
        # db.collection_name.aggregate()
        # db.collection_name.findOne()
        # collection_name.find()
        # getCollection("collection_name")
        
        mongo_patterns = [
            r'db\.(\w+)\.(?:find|insertOne|insertMany|updateOne|updateMany|deleteOne|deleteMany|aggregate|findOne|count|distinct|createIndex|dropIndex)',
            r'["\'](\w+)["\']\.(?:find|insertOne|insertMany|updateOne|updateMany|deleteOne|deleteMany|aggregate|findOne)',
            r'getCollection\s*\(["\'](\w+)["\']',
            r'collection\s*=\s*["\'](\w+)["\']',
            r'["\']collection["\']\s*:\s*["\'](\w+)["\']',
            r'\.collection\s*\(["\'](\w+)["\']',
        ]
        
        for line_num, line in enumerate(lines, 1):
            for pattern in mongo_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    collection_name = match.group(1)
                    # Skip common non-collection names
                    if collection_name.lower() not in ['db', 'client', 'database', 'mongo', 'mongodb']:
                        collections.append((collection_name, line_num, line.strip()))
        
        return collections

