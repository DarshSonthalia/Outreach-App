FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy application
COPY . .

# Build the application
RUN npm run build

# Set environment
ENV NODE_ENV=production

# Expose port
EXPOSE 3000

# Run the application
CMD ["npm", "start"]
