# Flask Assignment Server

## Description

Flask Assignment Server is a web application built using Flask to manage assignments, check usernames, and integrate with AWS buckets.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Directory Structure](#directory-structure)
- [Contributing](#contributing)
- [License](#license)

## Features

- Username syntax check
- AWS bucket integration
- Basic routes and configuration

## Installation

### Prerequisites

- Python 3.6 or higher
- `pip` (Python package installer)

### Setup

1. Clone the repository:

    ```sh
    git clone https://github.com/your-username/flask-assignment-server.git
    cd flask-assignment-server
    ```

2. Create and activate a virtual environment:

    ```sh
    python3 -m venv venv
    source venv/bin/activate  # On macOS and Linux
    # OR
    venv\Scripts\activate  # On Windows
    ```

3. Install the required packages:

    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. Ensure you have configured your environment variables (e.g., AWS credentials).
2. Run the application:

    ```sh
    python app/app.py
    ```

## Directory Structure

```
flask-assignment-server/
├── .flask_session/
├── .gitignore
├── app.py
├── LICENSE
├── Procfile
├── README.md
└── requirements.txt
```

## Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
