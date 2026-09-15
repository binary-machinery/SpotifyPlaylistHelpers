# Non-secret, environment-specific settings that config.json is rendered from. The
# secrets alongside these (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, FLASK_SECRET_KEY)
# are SecureStrings put in by hand, deliberately outside Terraform so they stay out of
# state. Parameter names match the placeholders in configs/config_template.json.

resource "aws_ssm_parameter" "server_host" {
  name = "/sph/${var.env}/SERVER_HOST"
  type = "String"

  # The origin the app builds its Spotify redirect_uri from, so it needs the scheme and
  # no trailing slash. Becomes https:// once the load balancer has a certificate.
  value = "http://${aws_lb.application.dns_name}"
}
