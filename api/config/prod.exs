import Config

# Force using SSL in production. This also sets the "strict-security-transport" header,
# known as HSTS. If you have a health check endpoint, you may want to exclude it below.
# Note `:force_ssl` is required to be set at compile-time.
# Set FORCE_SSL=false at build time (the Docker image does) to serve plain HTTP, e.g. on a team server
# without a TLS proxy.
if System.get_env("FORCE_SSL") != "false" do
  config :api, ApiWeb.Endpoint,
    force_ssl: [rewrite_on: [:x_forwarded_proto]],
    exclude: [
      # paths: ["/health"],
      hosts: ["localhost", "127.0.0.1"]
    ]
end

config :logger, level: :info

# Runtime production configuration, including reading
# of environment variables, is done on config/runtime.exs.
