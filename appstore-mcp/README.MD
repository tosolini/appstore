# create dockerfile lock before building:
cd appstore-mcp
docker build -f Dockerfile-lock -t temp-lock .
docker run --rm temp-lock > package-lock.json
rm Dockerfile-lock temp-lock
cd ..

# Build MCP (only first time or after changes):
docker build -t appstore-mcp ./appstore-mcp

# with docker-compose:
docker compose up -d appstore  # start appstore
docker compose build appstore-mcp

# with docker run:
docker run --rm -i --network appstore-net --name appstore-mcp-temp appstore-mcp

# with mcp:
cd appstore/  # root workspace
docker compose run --rm -i appstore-mcp


