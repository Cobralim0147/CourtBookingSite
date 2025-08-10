from config_loader import ConfigLoader
from CLI_Utilities import CLI

def main():
    """Main entry point for the Court Booking System."""
    try:
        # Load configuration
        config = ConfigLoader().config
        
        # Initialize and run CLI
        cli = CLI(config)
        cli.run()
        
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()