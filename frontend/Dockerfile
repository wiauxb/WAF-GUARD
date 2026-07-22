# Use the latest LTS version of Node.js
FROM node:25
 
# Set the working directory inside the container
WORKDIR /app

# Copy the rest of your application files
COPY . .

WORKDIR /app/waf-react
 
# Install dependencies

# Commented out to avoid reinstalling node_modules on dev setup.
# Uncomment for production builds and remove volume mapping in docker-compose.yaml 
#RUN npm install

# Keep container running for debugging (remove this in production)
# CMD ["sleep", "infinity"]