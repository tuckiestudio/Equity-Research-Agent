FROM node:18-alpine

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

# Create non-root user for security
RUN adduser -D appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
