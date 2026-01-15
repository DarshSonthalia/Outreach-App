FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy application
COPY . .

# Set environment
ENV NODE_ENV=development

# Expose port
EXPOSE 3000

# Run the application (overridden by compose, but good for base)
CMD ["npm", "run", "dev"]
