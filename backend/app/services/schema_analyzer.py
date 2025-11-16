"""
Database Schema Analyzer
Parses DDL changes and extracts table relationships
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TableColumn:
    """Represents a database column"""
    name: str
    data_type: str
    nullable: bool = True
    default_value: Optional[str] = None
    primary_key: bool = False
    foreign_key: Optional[Tuple[str, str]] = None  # (referenced_table, referenced_column)


@dataclass
class DatabaseTable:
    """Represents a database table"""
    name: str
    columns: List[TableColumn]
    indexes: List[str] = None
    foreign_keys: List[Dict] = None


@dataclass
class SchemaChange:
    """Represents a schema change"""
    change_type: str  # ADD_COLUMN, DROP_COLUMN, MODIFY_COLUMN, ADD_TABLE, DROP_TABLE, etc.
    table_name: str
    column_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    sql_statement: Optional[str] = None


class SchemaAnalyzer:
    """Analyzes database schema and DDL changes"""
    
    def __init__(self):
        self.tables: Dict[str, DatabaseTable] = {}
    
    def parse_ddl(self, ddl_content: str) -> Dict[str, DatabaseTable]:
        """
        Parse DDL SQL to extract table definitions
        
        Args:
            ddl_content: SQL DDL content (CREATE TABLE, ALTER TABLE, etc.)
        
        Returns:
            Dictionary of table_name -> DatabaseTable
        """
        tables = {}
        
        # Pattern to match CREATE TABLE statements
        create_table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?\s*\((.*?)\);?'
        
        matches = re.finditer(create_table_pattern, ddl_content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            table_name = match.group(1)
            table_body = match.group(2)
            
            columns = self._parse_columns(table_body)
            indexes = self._parse_indexes(table_body)
            foreign_keys = self._parse_foreign_keys(table_body)
            
            tables[table_name] = DatabaseTable(
                name=table_name,
                columns=columns,
                indexes=indexes or [],
                foreign_keys=foreign_keys or []
            )
        
        self.tables = tables
        return tables
    
    def _parse_columns(self, table_body: str) -> List[TableColumn]:
        """Parse column definitions from table body"""
        columns = []
        
        # Split by comma, but be careful with nested parentheses
        lines = self._smart_split(table_body, ',')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('INDEX') or line.startswith('FOREIGN KEY') or line.startswith('PRIMARY KEY'):
                continue
            
            # Match column definition: name type [constraints]
            col_match = re.match(
                r'`?(\w+)`?\s+(\w+(?:\([^)]+\))?)\s*(.*)',
                line,
                re.IGNORECASE
            )
            
            if col_match:
                col_name = col_match.group(1)
                data_type = col_match.group(2)
                constraints = col_match.group(3)
                
                nullable = 'NOT NULL' not in constraints.upper()
                primary_key = 'PRIMARY KEY' in constraints.upper()
                
                # Extract default value
                default_match = re.search(r'DEFAULT\s+([^,\s]+)', constraints, re.IGNORECASE)
                default_value = default_match.group(1) if default_match else None
                
                columns.append(TableColumn(
                    name=col_name,
                    data_type=data_type,
                    nullable=nullable,
                    default_value=default_value,
                    primary_key=primary_key
                ))
        
        return columns
    
    def _parse_indexes(self, table_body: str) -> List[str]:
        """Parse index definitions"""
        indexes = []
        
        index_pattern = r'INDEX\s+(?:`?(\w+)`?\s+)?\(([^)]+)\)'
        matches = re.finditer(index_pattern, table_body, re.IGNORECASE)
        
        for match in matches:
            index_name = match.group(1) or "unnamed"
            columns = match.group(2)
            indexes.append(f"{index_name}({columns})")
        
        return indexes
    
    def _parse_foreign_keys(self, table_body: str) -> List[Dict]:
        """Parse foreign key constraints"""
        foreign_keys = []
        
        fk_pattern = r'FOREIGN\s+KEY\s+\(`?(\w+)`?\)\s+REFERENCES\s+`?(\w+)`?\(`?(\w+)`?\)'
        matches = re.finditer(fk_pattern, table_body, re.IGNORECASE)
        
        for match in matches:
            foreign_keys.append({
                "column": match.group(1),
                "references_table": match.group(2),
                "references_column": match.group(3)
            })
        
        return foreign_keys
    
    def _smart_split(self, text: str, delimiter: str) -> List[str]:
        """Split text by delimiter, respecting parentheses"""
        result = []
        current = ""
        depth = 0
        
        for char in text:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
            elif char == delimiter and depth == 0:
                if current.strip():
                    result.append(current.strip())
                current = ""
                continue
            
            current += char
        
        if current.strip():
            result.append(current.strip())
        
        return result
    
    def parse_schema_change(self, sql_statement: str) -> Optional[SchemaChange]:
        """
        Parse a schema change SQL statement (ALTER TABLE, etc.)
        Handles both complete and incomplete SQL statements.
        
        Args:
            sql_statement: SQL DDL statement (may be incomplete)
        
        Returns:
            SchemaChange object or None
        """
        sql_upper = sql_statement.upper().strip()
        
        # Handle truncated/incomplete SQL (ends with ...)
        if sql_upper.endswith('...'):
            sql_upper = sql_upper[:-3].strip()
        
        # Extract table name (handle schema.table format)
        # Pattern: ALTER TABLE [schema.]table_name ...
        table_match = re.match(
            r'ALTER\s+TABLE\s+(?:`?(\w+)`?\.)?`?(\w+)`?',
            sql_upper,
            re.IGNORECASE
        )
        
        if not table_match:
            # Try DROP TABLE
            drop_table_match = re.match(
                r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:`?(\w+)`?\.)?`?(\w+)`?',
                sql_upper,
                re.IGNORECASE
            )
            if drop_table_match:
                schema = drop_table_match.group(1)
                table_name = drop_table_match.group(2)
                full_table_name = f"{schema}.{table_name}" if schema else table_name
                return SchemaChange(
                    change_type="DROP_TABLE",
                    table_name=table_name.upper(),  # Store just table name, uppercase
                    sql_statement=sql_statement
                )
            return None
        
        schema = table_match.group(1)
        table_name = table_match.group(2)
        full_table_name = f"{schema}.{table_name}" if schema else table_name
        
        # Try to extract operation type and details
        # ALTER TABLE table_name ADD COLUMN column_name ...
        add_col_match = re.search(
            r'ADD\s+COLUMN\s+`?(\w+)`?\s+(\w+(?:\([^)]+\))?)',
            sql_upper,
            re.IGNORECASE
        )
        if add_col_match:
            return SchemaChange(
                change_type="ADD_COLUMN",
                table_name=table_name.upper(),
                column_name=add_col_match.group(1).upper(),
                new_value=add_col_match.group(2),
                sql_statement=sql_statement
            )
        
        # ALTER TABLE table_name DROP COLUMN column_name
        # Try more flexible patterns to handle incomplete SQL
        drop_col_match = re.search(
            r'DROP\s+(?:COLUMN\s+)?`?(\w+)`?',
            sql_upper,
            re.IGNORECASE
        )
        if drop_col_match:
            # Make sure it's not DROP TABLE
            if 'TABLE' not in sql_upper or sql_upper.find('DROP') < sql_upper.find('TABLE'):
                column_name = drop_col_match.group(1)
                # Verify it's not a table name (heuristic: if it's the same as table_name, might be wrong)
                if column_name.upper() != table_name.upper():
                    return SchemaChange(
                        change_type="DROP_COLUMN",
                        table_name=table_name.upper(),
                        column_name=column_name.upper(),
                        sql_statement=sql_statement
                    )
        
        # ALTER TABLE table_name MODIFY COLUMN column_name ...
        modify_col_match = re.search(
            r'MODIFY\s+COLUMN\s+`?(\w+)`?\s+(\w+(?:\([^)]+\))?)',
            sql_upper,
            re.IGNORECASE
        )
        if modify_col_match:
            return SchemaChange(
                change_type="MODIFY_COLUMN",
                table_name=table_name.upper(),
                column_name=modify_col_match.group(1).upper(),
                new_value=modify_col_match.group(2),
                sql_statement=sql_statement
            )
        
        # ALTER TABLE table_name ALTER COLUMN column_name ... (PostgreSQL syntax)
        alter_col_match = re.search(
            r'ALTER\s+COLUMN\s+`?(\w+)`?\s+(\w+(?:\([^)]+\))?)',
            sql_upper,
            re.IGNORECASE
        )
        if alter_col_match:
            return SchemaChange(
                change_type="MODIFY_COLUMN",
                table_name=table_name.upper(),
                column_name=alter_col_match.group(1).upper(),
                new_value=alter_col_match.group(2) if alter_col_match.lastindex >= 2 else None,
                sql_statement=sql_statement
            )
        
        # ALTER TABLE table_name RENAME COLUMN old_name TO new_name
        rename_col_match = re.search(
            r'RENAME\s+COLUMN\s+`?(\w+)`?\s+TO\s+`?(\w+)`?',
            sql_upper,
            re.IGNORECASE
        )
        if rename_col_match:
            return SchemaChange(
                change_type="RENAME_COLUMN",
                table_name=table_name.upper(),
                column_name=rename_col_match.group(1).upper(),
                old_value=rename_col_match.group(1).upper(),
                new_value=rename_col_match.group(2).upper(),
                sql_statement=sql_statement
            )
        
        # If we only have "ALTER TABLE table_name" without operation details,
        # return a generic ALTER_TABLE change (we'll need to query DB for details)
        if sql_upper.startswith('ALTER TABLE'):
            return SchemaChange(
                change_type="ALTER_TABLE",  # Generic - operation unknown
                table_name=table_name.upper(),
                sql_statement=sql_statement
            )
        
        # DROP TABLE table_name
        drop_table_match = re.match(
            r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:`?(\w+)`?\.)?`?(\w+)`?',
            sql_upper,
            re.IGNORECASE
        )
        if drop_table_match:
            schema = drop_table_match.group(1)
            table_name = drop_table_match.group(2)
            return SchemaChange(
                change_type="DROP_TABLE",
                table_name=table_name.upper(),
                sql_statement=sql_statement
            )
        
        return None
    
    def get_table_relationships(self, table_name: str) -> Dict:
        """
        Get all relationships for a table (foreign keys, referenced by, etc.)
        
        Returns:
            Dictionary with forward and reverse relationships
        """
        if table_name not in self.tables:
            return {"forward": [], "reverse": []}
        
        table = self.tables[table_name]
        forward = []
        reverse = []
        
        # Forward: tables this table references (foreign keys)
        for fk in table.foreign_keys or []:
            forward.append({
                "type": "FOREIGN_KEY",
                "target_table": fk["references_table"],
                "column": fk["column"],
                "references_column": fk["references_column"]
            })
        
        # Reverse: tables that reference this table
        for other_table_name, other_table in self.tables.items():
            if other_table_name == table_name:
                continue
            
            for fk in other_table.foreign_keys or []:
                if fk["references_table"] == table_name:
                    reverse.append({
                        "type": "REFERENCED_BY",
                        "source_table": other_table_name,
                        "column": fk["column"],
                        "references_column": fk["references_column"]
                    })
        
        return {
            "forward": forward,
            "reverse": reverse
        }

