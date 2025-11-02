FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Set environment variable
ENV REACT_APP_API_URL=http://localhost:8000

# Start development server
CMD ["npm", "start"]