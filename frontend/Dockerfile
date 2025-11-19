# Use the latest LTS version of Node.js
FROM node:25-alpine
 
# Set the working directory inside the container
WORKDIR /app

# Copy the rest of your application files
COPY . .

WORKDIR /app/waf-react
 
# Install dependencies
RUN npm install

# Keep container running for debugging (remove this in production)
# CMD ["sleep", "infinity"]