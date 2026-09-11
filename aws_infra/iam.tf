resource "aws_iam_role" "SPH_EC2_role" {
  name = "SPH-EC2-role"
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

resource "aws_iam_role_policy_attachment" "allow_ecr_pull" {
  role = aws_iam_role.SPH_EC2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly"
}

resource "aws_iam_instance_profile" "SPH_EC2_instance_profile" {
  name = "SPH-EC2-instance-profile"
  role = aws_iam_role.SPH_EC2_role.name
}
