#!/bin/bash

# Function to install Homebrew (macOS)
install_homebrew() {
    if ! command -v brew > /dev/null 2>&1; then
        echo "Homebrew is not installed. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/$(whoami)/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        echo "Homebrew is already installed."
    fi
}

# Function to install PostgreSQL using Homebrew (macOS)
install_postgresql_mac() {
    install_homebrew

    if ! brew list postgresql > /dev/null 2>&1; then
        echo "Installing PostgreSQL..."
        brew install postgresql
    else
        echo "PostgreSQL is already installed."
    fi

    echo "Starting PostgreSQL service..."
    brew services start postgresql
}

# Function to install PostgreSQL using apt-get (Linux)
install_postgresql_linux() {
    if command -v psql > /dev/null 2>&1; then
        echo "PostgreSQL is already installed."
    else
        echo "Installing PostgreSQL..."
        sudo apt-get update
        sudo apt-get install -y postgresql postgresql-contrib
    fi

    echo "Starting PostgreSQL service..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
}

# Generate the .env file
generate_env_file() {
    echo "Generating .env file..."

    cat <<EOF > .env
DB_NAME=study_stream_db
DB_USER=study_stream_db_admin
DB_PASSWORD=study_stream_db_psw
DB_HOST=localhost
DB_PORT=5432
EOF

    echo ".env file created with database settings."
}

# Check the operating system and install PostgreSQL accordingly
OS_TYPE=$(uname)
if [ "$OS_TYPE" == "Darwin" ]; then
    install_postgresql_mac
elif [ "$OS_TYPE" == "Linux" ]; then
    install_postgresql_linux
else
    echo "Unsupported OS: $OS_TYPE"
    exit 1
fi

# Set environment variables for PostgreSQL from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo ".env file not found. Generating a new one."
    generate_env_file
    export $(grep -v '^#' .env | xargs)
fi

# Ensure environment variables are set
if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ] || [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ]; then
    echo "One or more environment variables are not set. Please check the .env file."
    exit 1
fi

# Initialize PostgreSQL cluster if not already initialized
if [ "$OS_TYPE" == "Darwin" ]; then
    PGDATA="/usr/local/var/postgres"
    if [ ! -d "$PGDATA" ]; then
        echo "Initializing PostgreSQL cluster..."
        initdb -D $PGDATA
    fi
elif [ "$OS_TYPE" == "Linux" ]; then
    PGDATA="/var/lib/postgresql/13/main"
    if [ ! -d "$PGDATA" ]; then
        echo "Initializing PostgreSQL cluster..."
        sudo -u postgres /usr/lib/postgresql/13/bin/initdb -D $PGDATA
    fi
fi

# Start PostgreSQL service
if [ "$OS_TYPE" == "Darwin" ]; then
    brew services start postgresql
elif [ "$OS_TYPE" == "Linux" ]; then
    sudo systemctl start postgresql
fi

# Create database and user
echo "Creating database and user..."
if [ "$OS_TYPE" == "Darwin" ]; then
    psql postgres -c "CREATE DATABASE $DB_NAME;"
    psql postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
elif [ "$OS_TYPE" == "Linux" ]; then
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
fi

echo "PostgreSQL setup complete."
