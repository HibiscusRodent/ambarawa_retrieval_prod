

def check_table_exists(active_db, table_name):
    """
    A simple function to open a table in the lanceDB instance. Since
    we use `open_table` method instead of create, it will return
    error if the table does not exist.

    In that case, it will stop the process and notify the user to create the table first before proceeding. It will also return
    a list of tables that is available given the current db
    instance.
    
    Parameters:
    lance_db (AsyncConnection): The lanceDB instance connection.
    table_name (str): The name of the table to open.
    
    Returns:
    The active table object, that is typed as AsyncTable.
    
    """
    try:
        active_tbl = active_db.open_table(table_name)
        print(f"Successfully opened table: {table_name}")
        return active_tbl
    
    except Exception as e:
        print("Please create the table before proceeding. Table may not exist yet.")
        print(f"Here's a list of the available tables: {active_db.list_tables()}")
        raise RuntimeError(f"Failed to open table '{table_name}': {e}") from e
    return None

# example usage:
# lance_db_uri = "data/test/lance_db_semi_prod"
# active_db = lancedb.connect(lance_db_uri)
# table_name = "active_table_lots_columns"
# check_table_exists(active_db, table_name)

def main():
    return None

if __name__ == "__main__":
    main()