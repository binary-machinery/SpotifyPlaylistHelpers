resource "aws_ecr_repository" "application" {
  name = "spotify-playlist-helpers"
  image_tag_mutability = "IMMUTABLE_WITH_EXCLUSION"

  image_tag_mutability_exclusion_filter {
    filter = "*-dev"
    filter_type = "WILDCARD"
  }

  tags = {
    Name = "spotify-playlist-helpers"
  }
}
