FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY frontend/package.json .
COPY frontend/package-lock.json .
RUN npm install

# Expose port
EXPOSE 5173

# Run the development server
CMD ["npm", "run", "dev"]
