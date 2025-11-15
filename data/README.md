# Finclator Seed Data

This directory contains JSON files used to seed the Finclator database with initial data.

## Files

### `finance_schools.json`

Defines the finance theory schools used to categorize influencers.

**Format:**
```json
[
  {
    "name": "School Name",
    "description": "Description of the investment philosophy"
  }
]
```

**Default Schools:**
- **Macro**: Focus on macroeconomic trends, monetary policy, and global markets
- **Technical**: Technical analysis, chart patterns, and trading indicators
- **Value**: Value investing, fundamental analysis, and long-term holdings
- **Growth**: Growth investing, innovation, and momentum strategies

### `influencers.json`

Defines the X (Twitter) influencers to track for market sentiment.

**Format:**
```json
[
  {
    "x": "X_username",
    "display_name": "Full Display Name",
    "finance_school": "School Name",
    "notes": "Optional notes about the influencer"
  }
]
```

**Fields:**
- `x` (required): X/Twitter username without the @ symbol
- `display_name` (required): Full name or display name
- `finance_school` (required): Must match a school name from `finance_schools.json`
- `notes` (optional): Additional context (not stored in database, just for reference)

**Example Influencers:**
The provided list includes well-known market commentators across different schools:
- Peter Schiff, Raoul Pal (Macro)
- Tone Vays, Peter Brandt (Technical)
- Michael Saylor, Jack Dorsey (Value)
- Cathie Wood, Chamath Palihapitiya (Growth)

## Usage

### Initial Seeding

```bash
python scripts/seed_data.py
```

### Re-seeding After Changes

If you modify these files and want to update the database:

```bash
# Clear existing data (optional)
psql -d finclator -c "TRUNCATE influencers, finance_schools CASCADE;"

# Re-seed
python scripts/seed_data.py
```

### Adding New Influencers

1. Edit `data/influencers.json`
2. Add new entries with valid X handles
3. Ensure `finance_school` matches an existing school
4. Run seed script

### Adding New Schools

1. Edit `data/finance_schools.json`
2. Add new school definitions
3. Update influencers to use the new school if needed
4. Run seed script

## Validation

The seed script will:
- ✅ Validate that all schools are created before influencers
- ✅ Skip influencers with unknown finance schools (with warning)
- ✅ Show counts of created records

## Notes

- **X Usernames**: Ensure usernames (without @) are valid and active X accounts
- **Rate Limits**: Be mindful of X API rate limits when adding many influencers
- **Duplicates**: The script doesn't check for duplicates - clear the database first if re-seeding
- **Real Data**: The provided handles are real accounts, but verify they're still active and relevant for your analysis

## Customization

Feel free to:
- Add your own finance schools (e.g., "Crypto Native", "Contrarian", "Quantitative")
- Replace influencers with domain experts relevant to your focus
- Add more or fewer influencers per school based on your needs
- Remove schools you don't want to track

The system is flexible and will work with any school structure you define!

