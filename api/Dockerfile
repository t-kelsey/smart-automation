ARG ELIXIR_VERSION=1.19.5
ARG OTP_VERSION=28.1.1
ARG DEBIAN_VERSION=trixie-20260202-slim

FROM docker.io/hexpm/elixir:${ELIXIR_VERSION}-erlang-${OTP_VERSION}-debian-${DEBIAN_VERSION} AS build
RUN apt-get update -y && apt-get install -y build-essential git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mix local.hex --force && mix local.rebar --force
ENV MIX_ENV=prod
# Serve plain HTTP (the compose stack has no TLS proxy); see config/prod.exs
ENV FORCE_SSL=false
COPY mix.exs mix.lock ./
RUN mix deps.get --only prod
COPY config config
RUN mix deps.compile
COPY priv priv
COPY lib lib
RUN mix compile
COPY config/runtime.exs config/
RUN mix release

FROM debian:trixie-slim
RUN apt-get update -y && apt-get install -y libstdc++6 openssl libncurses6 locales ca-certificates && rm -rf /var/lib/apt/lists/*
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8 PHX_SERVER=true MIX_ENV=prod \
    DOCUMENT_STORAGE_DIR=/data/storage
WORKDIR /app
RUN useradd --create-home app && mkdir -p /data/storage && chown -R app /app /data
COPY --from=build --chown=app /app/_build/prod/rel/api ./
USER app
EXPOSE 4000
# Apply migrations (creates the PostGIS extension too), optionally load the mock data
# (SEED_MOCK_DATA=true, see .env.example), then start the server
CMD ["sh", "-c", "bin/api eval 'Api.Release.migrate()' && { [ \"$SEED_MOCK_DATA\" != true ] || bin/api eval 'Api.Release.seed()'; } && exec bin/api start"]
