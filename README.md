# smart-automation

**Challenge**

Automated extraction and standardisation of drilling data for a global geodatabase (By Herrenknecht AG).

[Hackathon Portal](https://hackathon.badencampus.de/en/challenges/66f8c41f-b62a-4a84-a356-79546bc9c68b)

[Herrenknecht fileshare](https://fileshare.herrenknecht.com/download;jsessionid=node0sfhoqch7owhb1ozu1tbebpev151416.node0?0&id=Soq0VEfmJL)
Passwort: siehe email

# Development Setup

Postgres database is required. Either as docker container or installed locally.

```bash
# Start api
cd api
mix ecto.create     # Create the database
mix ecto.migrate    # Run database migrations
mix phx.server      # Start development server
```

```
# Start web
cd web
pnpm install        # Install web dependencies
pnpm run            # Start web development server
```

# Miscellaneous

Kai was here
