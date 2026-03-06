resource "aws_lambda_function" "processor" {
  function_name = "data-processor"
  runtime       = "python3.13"
  handler       = "main.handler"
  filename      = "lambda.zip"
  memory_size   = 256
  timeout       = 30

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.events.name
      BUCKET     = aws_s3_bucket.data.id
    }
  }

  tags = {
    Environment = "production"
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.processor.function_name
  principal     = "apigateway.amazonaws.com"
}
