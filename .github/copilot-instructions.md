# Copilot Instructions for Rowing Lineup Setter

## Project Overview
This is a rowing lineup setter application designed to help coaches set lineups more quickly and efficiently.

## Project Goals
- Create an intuitive interface for rowing coaches to manage team lineups
- Optimize lineup creation based on athlete performance and positions
- Streamline the coaching workflow for rowing team management

## Development Guidelines

### Code Style
- Follow clean code principles with clear, descriptive naming
- Keep functions focused and modular
- Add comments for complex logic, especially lineup optimization algorithms
- Use consistent formatting throughout the codebase

### Testing
- Write tests for core lineup logic and algorithms
- Include edge cases (e.g., odd number of rowers, missing positions)
- Test user input validation

### Best Practices
- Prioritize user experience for coaches who may not be technical
- Ensure data validation for roster and lineup inputs
- Consider performance for larger team rosters
- Document any rowing-specific terminology or conventions

## Project Structure
This is an early-stage project. As the codebase grows:
- Separate concerns (UI, business logic, data models)
- Keep configuration files in the root directory
- Place tests alongside source files or in a dedicated test directory

## Domain Knowledge
- **Rowing positions**: Boats have specific seat positions (e.g., bow, stern, stroke)
- **Port/Starboard**: Rowers typically have a preferred side
- **Boat types**: Different boats (e.g., 4+, 8+, 2x) have different crew sizes
- **Skill levels**: Consider athlete experience and skill when creating lineups

## Future Considerations
- Mobile-friendly interface for on-the-go lineup changes
- Historical performance tracking
- Integration with rowing club management systems
- Export capabilities for sharing lineups
