-- Создаем пользователя для бэкапов
CREATE USER backup_user WITH PASSWORD '${BACKUP_PASSWORD}';
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO backup_user;

-- Создаем расширения
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Настраиваем параметры для производительности
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;
ALTER SYSTEM SET effective_cache_size = '2GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Создаем схему для партиционирования
CREATE SCHEMA IF NOT EXISTS partitions;

-- Функция для создания партиций
CREATE OR REPLACE FUNCTION create_monthly_partition(
    parent_table TEXT,
    partition_date DATE
) RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    partition_start DATE;
    partition_end DATE;
BEGIN
    partition_start := date_trunc('month', partition_date);
    partition_end := partition_start + INTERVAL '1 month';
    partition_name := parent_table || '_' || to_char(partition_start, 'YYYY_MM');
    
    EXECUTE format(
        'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        parent_table,
        partition_start,
        partition_end
    );
    
    -- Создаем индексы для партиции
    EXECUTE format('CREATE INDEX ON %I (patient_id)', partition_name);
    EXECUTE format('CREATE INDEX ON %I (doctor_id)', partition_name);
    EXECUTE format('CREATE INDEX ON %I (scheduled_start)', partition_name);
END;
$$ LANGUAGE plpgsql;

-- Функция для очистки старых данных
CREATE OR REPLACE FUNCTION cleanup_old_data(
    table_name TEXT,
    retention_months INTEGER DEFAULT 36
) RETURNS VOID AS $$
DECLARE
    cutoff_date DATE;
    partition RECORD;
BEGIN
    cutoff_date := CURRENT_DATE - (retention_months || ' months')::INTERVAL;
    
    FOR partition IN
        SELECT inhrelid::regclass AS partition_name
        FROM pg_inherits
        WHERE inhparent = table_name::regclass
    LOOP
        -- Удаляем партиции старше retention_months
        IF partition.partition_name::TEXT LIKE '%_20%' THEN
            -- Извлекаем дату из имени партиции
            CONTINUE WHEN (
                TO_DATE(
                    SUBSTRING(partition.partition_name::TEXT FROM '_(\d{4}_\d{2})$'),
                    'YYYY_MM'
                ) < cutoff_date
            );
            
            EXECUTE format('DROP TABLE IF EXISTS %I', partition.partition_name);
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;