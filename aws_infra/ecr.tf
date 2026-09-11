resource "aws_ecr_repository" "spotify_playlist_helpers" {
  name = "spotify-playlist-helpers"
  image_tag_mutability = "IMMUTABLE_WITH_EXCLUSION"

  image_tag_mutability_exclusion_filter {
    filter = "*-dev"
    filter_type = "WILDCARD"
  }
}
