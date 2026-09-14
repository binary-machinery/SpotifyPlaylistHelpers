resource "aws_iam_role" "application" {
  name = "sph-${var.env}-application"
  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
  })
}

resource "aws_iam_instance_profile" "application" {
  name = "sph-${var.env}-application"
  role = aws_iam_role.application.name
}

resource "aws_iam_role_policy_attachment" "allow_ecr_pull" {
  role = aws_iam_role.application.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly"
}
