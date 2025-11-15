"""Seed initial data for Finclator - influencers and finance schools."""
import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.session import AsyncSessionLocal
from src.db.models import FinanceSchool, Influencer


def load_json_data(filename: str) -> list:
    """Load data from JSON file in data/ directory."""
    data_dir = Path(__file__).parent.parent / "data"
    file_path = data_dir / filename
    
    if not file_path.exists():
        print(f"⚠ Warning: {file_path} not found")
        return []
    
    with open(file_path, 'r') as f:
        return json.load(f)


async def seed_data():
    """Seed finance schools and influencers from JSON files."""
    print("🌱 Seeding Finclator database...")
    
    # Load data from JSON files
    schools_data = load_json_data("finance_schools.json")
    influencers_data = load_json_data("influencers.json")
    
    if not schools_data:
        print("✗ No finance schools data found. Exiting.")
        return
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        # Create or get finance schools
        school_map = {}  # name -> school object
        created_schools = 0
        existing_schools = 0
        
        for school_data in schools_data:
            # Check if school already exists
            result = await session.execute(
                select(FinanceSchool).where(FinanceSchool.name == school_data["name"])
            )
            school = result.scalar_one_or_none()
            
            if school:
                existing_schools += 1
                school_map[school.name] = school
            else:
                school = FinanceSchool(
                    name=school_data["name"],
                    description=school_data["description"]
                )
                session.add(school)
                await session.flush()  # Flush to get ID
                await session.refresh(school)
                created_schools += 1
                school_map[school.name] = school
        
        await session.commit()
        
        if created_schools > 0:
            print(f"✓ Created {created_schools} finance schools")
        if existing_schools > 0:
            print(f"ℹ {existing_schools} finance schools already exist")
        
        # Create or get influencers if data exists
        if influencers_data:
            created_influencers = 0
            existing_influencers = 0
            skipped_influencers = 0
            
            for inf_data in influencers_data:
                school_name = inf_data["finance_school"]
                x_handle = inf_data["x"]
                
                if school_name not in school_map:
                    print(f"⚠ Warning: Unknown finance school '{school_name}' for @{x_handle}, skipping")
                    skipped_influencers += 1
                    continue
                
                # Check if influencer already exists
                result = await session.execute(
                    select(Influencer).where(Influencer.handle == x_handle)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    existing_influencers += 1
                else:
                    influencer = Influencer(
                        handle=x_handle,
                        display_name=inf_data["display_name"],
                        finance_school_id=school_map[school_name].id,
                    )
                    session.add(influencer)
                    created_influencers += 1
            
            await session.commit()
            
            if created_influencers > 0:
                print(f"✓ Created {created_influencers} influencers")
            if existing_influencers > 0:
                print(f"ℹ {existing_influencers} influencers already exist")
            if skipped_influencers > 0:
                print(f"⚠ Skipped {skipped_influencers} influencers (unknown schools)")
        else:
            print("⚠ No influencers data found, skipping")
        
        print("\n✅ Database seeded successfully!")
        print("\nData files:")
        print("  - data/finance_schools.json - Finance school definitions")
        print("  - data/influencers.json - Influencer X handles and schools")
        print("\nNext steps:")
        print("1. Edit data/influencers.json to add/modify influencers")
        print("2. Run workers to start ingesting data: ./scripts/run_pipeline.sh")
        print("3. Start the API: uvicorn src.api.main:app --reload")


if __name__ == "__main__":
    asyncio.run(seed_data())

