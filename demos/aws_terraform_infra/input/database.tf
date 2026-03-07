# --- DynamoDB Table ---

resource "aws_dynamodb_table" "main" {
  name         = "${local.name_prefix}-records"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "gsi1pk"
    type = "S"
  }

  attribute {
    name = "gsi1sk"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "gsi1pk"
    range_key       = "gsi1sk"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }

  tags = { Component = "database" }
}

# --- RDS PostgreSQL ---

resource "aws_db_instance" "postgres" {
  identifier             = "${local.name_prefix}-postgres"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = var.rds_instance_class
  allocated_storage      = 50
  max_allocated_storage  = 200
  db_name                = "appdb"
  username               = "dbadmin"
  password               = aws_secretsmanager_secret_version.db_password.secret_string
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  multi_az               = var.environment == "production"
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.main.arn
  skip_final_snapshot    = var.environment != "production"
  backup_retention_period = 7

  tags = { Component = "database" }
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
}

# --- ElastiCache Redis ---

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${local.name_prefix}-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  num_cache_nodes      = 1
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  tags = { Component = "cache" }
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-cache-subnet"
  subnet_ids = aws_subnet.private[*].id
}
