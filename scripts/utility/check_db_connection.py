import os
import sys


print('DEBUG: script started')

# Load a .env file if it exists (optional)
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# Import DB helper functions - ensure repository root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
print('DEBUG: repo_root =', repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
print('DEBUG: sys.path[0:3] =', sys.path[:3])
try:
    from scripts.train_pa_outcome_distribution import database_kwargs, database_url
except Exception as e:
    sys.stderr.write(f'❌ Failed to import DB helpers: {e}\n')
    sys.exit(1)


def test_sqlalchemy():
    from sqlalchemy import create_engine, text

    engine = create_engine(database_url())
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ SQLAlchemy connection successful:', result.scalar())


def test_psycopg2():
    import psycopg2

    conn = psycopg2.connect(**database_kwargs())
    cur = conn.cursor()
    cur.execute('SELECT 1')
    print('✅ psycopg2 connection successful:', cur.fetchone()[0])
    cur.close()
    conn.close()


if __name__ == '__main__':
    try:
        test_sqlalchemy()
    except Exception as e_sql:
        sys.stderr.write(f'⚠️ SQLAlchemy failed: {e_sql}\n')
        try:
            test_psycopg2()
        except Exception as e_ps:
            sys.stderr.write(f'❌ psycopg2 also failed: {e_ps}\n')
            sys.exit(1)
