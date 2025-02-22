# Microservice-Based Order and Customer Management

This project is a microservices system built with Django that features separate services for customer and order management. It leverages Kafka for event streaming, PostgreSQL for data persistence, and Redis for caching popular items.

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Setup](#setup)
- [Local Development](#local-development)
  - [Setting Up Virtual Environments](#setting-up-virtual-environments)
  - [Connecting the Microservices Network for Kafka](#connecting-the-microservices-network-for-kafka)
  - [Installing Redis](#installing-redis)
- [Running the Application](#running-the-application)
- [API Overview](#api-overview)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

- **Customer Service**
  - Manages users and items.
  - Uses Redis to cache and rank top liked items.
  - Publishes item events (create, update, delete) to Kafka.
- **Order Service**
  - Handles order and item copy management.
  - Publishes order events to Kafka.
- **Event Streaming**
  - Utilizes Kafka & Zookeeper for asynchronous messaging between services.
- **Data Persistence**
  - Each microservice uses its own PostgreSQL instance.

## Architecture Overview

The system is composed of multiple Docker containers that include:
- **Kafka & Zookeeper:** For event streaming and asynchronous messaging.
- **PostgreSQL:** Separate databases for the Customer and Order services.
- **Redis:** For caching and managing like counts in the Customer service.
- **Django Applications:** Separate services for customer and order management, each running in its own container or virtual environment.

All containers communicate over a shared Docker network (`microservices_net`).

## Setup

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/Sudibya/Django_Task
   cd your-repo-name


Build and Run Containers:
Use Docker Compose to build and start all services. The Docker configuration includes Kafka, Zookeeper, PostgreSQL, Redis, and the Django apps.

bash
Copy
docker-compose up --build
