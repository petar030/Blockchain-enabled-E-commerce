# Blockchain E-commerce Backend

This project implements a full-featured e-commerce backend designed for multi-user operation. It is built using Python, Flask, and SQLAlchemy, with all services containerized using Docker for easy deployment and isolation. The system is architected with a clear separation between the authentication/authorization subsystem and the store management subsystem, enhancing security, modularity, and maintainability. 

Payments are handled via Ethereum smart contracts, with Ganache used to simulate the blockchain environment for development and testing. Each order generates a dedicated smart contract that ensures secure, verifiable payment and enforces conditional fund distribution: 80% to the store owner and 20% to the courier upon successful delivery confirmation. The system also ensures that couriers cannot process orders before payment is verified, maintaining transactional integrity.

The backend supports secure concurrent access and efficient handling of orders, user management, product catalogs, and order tracking. It demonstrates real-world practices in container orchestration, blockchain-based payment systems, and modular backend architecture suitable for scalable e-commerce applications.
