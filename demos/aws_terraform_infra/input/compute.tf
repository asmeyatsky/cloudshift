# --- Lambda Functions ---

resource "aws_lambda_function" "api_handler" {
  function_name = "${local.name_prefix}-api-handler"
  runtime       = "python3.11"
  handler       = "main.handler"
  role          = aws_iam_role.lambda_exec.arn
  filename      = "${path.module}/artifacts/api_handler.zip"
  memory_size   = 512
  timeout       = 30

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.main.name
      SQS_QUEUE_URL  = aws_sqs_queue.processing.url
      ENVIRONMENT    = local.environment
    }
  }

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  tags = { Component = "api" }
}

resource "aws_lambda_function" "stream_processor" {
  function_name = "${local.name_prefix}-stream-processor"
  runtime       = "nodejs18.x"
  handler       = "index.handler"
  role          = aws_iam_role.lambda_exec.arn
  filename      = "${path.module}/artifacts/stream_processor.zip"
  memory_size   = 256
  timeout       = 60
  reserved_concurrent_executions = 10

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.notifications.arn
    }
  }

  tags = { Component = "processing" }
}

# --- ECS Cluster & Service ---

resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_service" "backend" {
  name            = "${local.name_prefix}-backend-svc"
  cluster         = aws_ecs_cluster.main.id
  task_definition = "${local.name_prefix}-backend:1"
  desired_count   = var.ecs_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs.id]
  }
}

# --- EC2 Bastion Host ---

resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.bastion.id]
  iam_instance_profile   = aws_iam_instance_profile.bastion.name
  key_name               = var.ssh_key_name

  root_block_device {
    volume_size = 20
    encrypted   = true
  }

  tags = { Name = "${local.name_prefix}-bastion" }
}
