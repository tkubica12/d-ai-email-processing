"""
Company APIs Service - FastAPI implementation providing mock business data

This service provides HTTP endpoints for retrieving user products, financial scores,
and income data for use by AI agents in the submission analysis process.
"""

import os
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Security, Query, Path
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from dotenv import load_dotenv

from models import (
    UserProductsResponse,
    Product,
    FinancialScoreResponse,
    ScoreFactor,
    IncomeResponse,
    IncomeEntry,
    IncomeSource,
    ErrorResponse,
    ErrorDetails,
    ProductType,
    ProductStatus,
    ScoreType,
    Impact,
    IncomeType,
    Frequency,
    Granularity,
    ErrorCode
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress Azure SDK INFO logs to DEBUG level
logging.getLogger("azure").setLevel(logging.DEBUG)
logging.getLogger("azure.core").setLevel(logging.DEBUG)

# Initialize FastAPI app
app = FastAPI(
    title="Company APIs",
    description="Business-specific APIs providing internal company data and functionality",
    version="1.0.0",
    contact={
        "name": "Company APIs Team",
        "email": "support@example.com"
    }
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify JWT token - simplified for mock service
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        User ID extracted from token
        
    Raises:
        HTTPException: If token is invalid
    """
    # For mock implementation, accept any token and extract user ID
    # In production, this would validate JWT and extract user claims
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    # Mock token validation - in production, validate JWT signature and claims
    return "mock_user_id"

class MockDataGenerator:
    """Mock data generator for company APIs"""
    
    # Product pools for random selection
    PRODUCT_NAMES = {
        ProductType.banking: [
            "Premium Banking Package",
            "Business Banking Suite",
            "Personal Checking Plus",
            "Savings Maximizer",
            "Student Banking Bundle"
        ],
        ProductType.insurance: [
            "Life Insurance Premium",
            "Health Insurance Plus",
            "Auto Insurance Comprehensive",
            "Home Insurance Elite",
            "Travel Insurance Complete"
        ],
        ProductType.investment: [
            "Investment Portfolio Pro",
            "Retirement Planning Plus",
            "ETF Management Service",
            "Wealth Builder Package",
            "Tax-Advantaged Investing"
        ],
        ProductType.loan: [
            "Personal Loan Standard",
            "Home Mortgage Premium",
            "Auto Loan Express",
            "Student Loan Refinance",
            "Business Loan Flex"
        ],
        ProductType.credit: [
            "Credit Card Premium",
            "Business Credit Line",
            "Secured Credit Builder",
            "Cashback Rewards Card",
            "Travel Rewards Platinum"
        ],
        ProductType.other: [
            "Digital Services Package",
            "Consulting Services",
            "Premium Support Plan",
            "Business Advisory Service",
            "Financial Planning Package"
        ]
    }
    
    PRODUCT_FEATURES = {
        ProductType.banking: [
            "Unlimited transactions",
            "24/7 customer support",
            "Mobile banking app",
            "ATM fee reimbursement",
            "Online bill pay",
            "Wire transfer services",
            "Check deposit via app"
        ],
        ProductType.insurance: [
            "Comprehensive coverage",
            "24/7 claims support",
            "Multi-policy discount",
            "Accident forgiveness",
            "Roadside assistance",
            "Identity theft protection"
        ],
        ProductType.investment: [
            "Portfolio tracking",
            "Risk assessment",
            "Automated rebalancing",
            "Tax optimization",
            "Research tools",
            "Financial advisor access"
        ],
        ProductType.loan: [
            "Flexible repayment terms",
            "Rate protection",
            "No prepayment penalty",
            "Online account management",
            "Automatic payment discount"
        ],
        ProductType.credit: [
            "Rewards program",
            "Zero annual fee",
            "Purchase protection",
            "Extended warranty",
            "Fraud monitoring",
            "Credit score tracking"
        ],
        ProductType.other: [
            "24/7 customer support",
            "Priority service",
            "Custom solutions",
            "Dedicated account manager",
            "Regular reporting",
            "Flexible terms"
        ]
    }
    
    SCORE_FACTORS = {
        ScoreType.composite: [
            "Credit Score",
            "Debt-to-Income Ratio",
            "Savings Rate",
            "Payment History",
            "Account Age",
            "Income Stability"
        ],
        ScoreType.creditworthiness: [
            "Payment History",
            "Credit Utilization",
            "Length of Credit History",
            "Credit Mix",
            "New Credit Inquiries"
        ],
        ScoreType.liquidity: [
            "Cash Reserves",
            "Emergency Fund Coverage",
            "Liquid Asset Ratio",
            "Cash Flow Stability"
        ],
        ScoreType.stability: [
            "Income Consistency",
            "Employment History",
            "Expense Predictability",
            "Financial Volatility"
        ],
        ScoreType.growth: [
            "Income Growth Rate",
            "Asset Appreciation",
            "Investment Performance",
            "Savings Growth"
        ]
    }
    
    INCOME_SOURCES = [
        "Acme Corp Salary",
        "Freelance Consulting",
        "Investment Dividends",
        "Rental Property Income",
        "Side Business Revenue",
        "Bonus Payments",
        "Commission Income"
    ]
    
    @staticmethod
    def generate_user_products(user_id: str) -> UserProductsResponse:
        """Generate mock user products data"""
        # Seed random with user ID for consistent results
        # Use abs to ensure positive hash, and handle any string input
        seed_value = abs(hash(user_id)) % (2**32)
        random.seed(seed_value)
        
        # Generate 1-5 products
        num_products = random.randint(1, 5)
        products = []
        total_fees = 0.0
        
        for i in range(num_products):
            # Reset seed for each product to ensure consistency
            random.seed(seed_value + i)
            
            product_type = random.choice(list(ProductType))
            product_name = random.choice(MockDataGenerator.PRODUCT_NAMES[product_type])
            monthly_fee = round(random.uniform(9.99, 199.99), 2)
            
            # Generate features
            available_features = MockDataGenerator.PRODUCT_FEATURES[product_type]
            num_features = random.randint(2, min(len(available_features), 6))
            features = random.sample(available_features, num_features)
            
            product = Product(
                id=f"prod_{abs(hash(user_id + str(i))) % 100000:05d}",
                name=product_name,
                type=product_type,
                status=random.choice([ProductStatus.active, ProductStatus.inactive]),
                monthlyFee=monthly_fee,
                startDate=datetime.now(timezone.utc) - timedelta(days=random.randint(30, 1095)),
                endDate=datetime.now(timezone.utc) + timedelta(days=random.randint(30, 365)) if random.random() < 0.3 else None,
                features=features
            )
            
            products.append(product)
            if product.status == ProductStatus.active:
                total_fees += monthly_fee
        
        active_subscriptions = sum(1 for p in products if p.status == ProductStatus.active)
        
        return UserProductsResponse(
            userId=user_id,
            products=products,
            totalActiveSubscriptions=active_subscriptions,
            totalMonthlyFees=round(total_fees, 2)
        )
    
    @staticmethod
    def generate_financial_score(user_id: str, score_type: ScoreType) -> FinancialScoreResponse:
        """Generate mock financial score data"""
        # Seed random with user ID and score type for consistent results
        seed_value = abs(hash(user_id + score_type.value)) % (2**32)
        random.seed(seed_value)
        
        # Generate base score
        base_score = random.randint(60, 95)
        
        # Generate factors
        factor_names = MockDataGenerator.SCORE_FACTORS[score_type]
        factors = []
        
        for i, factor_name in enumerate(factor_names):
            # Use index to ensure consistent factor generation
            random.seed(seed_value + i)
            value = round(random.uniform(0.1, 1.0), 2)
            weight = round(random.uniform(0.1, 0.3), 2)
            impact = random.choice(list(Impact))
            
            factors.append(ScoreFactor(
                name=factor_name,
                value=value,
                weight=weight,
                impact=impact,
                description=f"Current {factor_name.lower()} indicates {impact.value} impact on overall score"
            ))
        
        # Generate recommendations
        recommendations = [
            "Consider increasing monthly savings contributions",
            "Explore debt consolidation options to improve debt-to-income ratio",
            "Maintain consistent payment history across all accounts",
            "Diversify investment portfolio to reduce risk",
            "Build emergency fund to 6 months of expenses"
        ]
        
        # Reset seed for recommendations selection
        random.seed(seed_value + 100)
        selected_recommendations = random.sample(recommendations, random.randint(2, 4))
        
        return FinancialScoreResponse(
            userId=user_id,
            scoreType=score_type,
            score=base_score,
            maxScore=100,
            scoreDate=datetime.now(timezone.utc),
            factors=factors,
            recommendations=selected_recommendations
        )
    
    @staticmethod
    def generate_income_data(user_id: str, start_date: datetime, end_date: datetime, granularity: Granularity) -> IncomeResponse:
        """Generate mock income data"""
        # Seed random with user ID for consistent results
        seed_value = abs(hash(user_id)) % (2**32)
        random.seed(seed_value)
        
        # Generate periods based on granularity
        periods = []
        current_date = start_date
        
        while current_date < end_date:
            if granularity == Granularity.daily:
                period_end = min(current_date + timedelta(days=1), end_date)
                period_id = current_date.strftime("%Y-%m-%d")
            elif granularity == Granularity.weekly:
                period_end = min(current_date + timedelta(weeks=1), end_date)
                period_id = current_date.strftime("%Y-W%U")
            elif granularity == Granularity.monthly:
                if current_date.month == 12:
                    period_end = current_date.replace(year=current_date.year + 1, month=1, day=1)
                else:
                    period_end = current_date.replace(month=current_date.month + 1, day=1)
                period_end = min(period_end, end_date)
                period_id = current_date.strftime("%Y-%m")
            else:  # yearly
                period_end = min(current_date.replace(year=current_date.year + 1), end_date)
                period_id = str(current_date.year)
            
            # Generate income sources for this period
            sources = []
            base_income = random.uniform(4000, 8000)
            
            # Primary salary
            sources.append(IncomeSource(
                source=random.choice(MockDataGenerator.INCOME_SOURCES),
                amount=round(base_income, 2),
                type=IncomeType.salary,
                frequency=Frequency.monthly
            ))
            
            # Additional sources (random chance)
            if random.random() < 0.3:
                sources.append(IncomeSource(
                    source="Freelance Work",
                    amount=round(random.uniform(500, 2000), 2),
                    type=IncomeType.freelance,
                    frequency=Frequency.monthly
                ))
            
            if random.random() < 0.2:
                sources.append(IncomeSource(
                    source="Investment Returns",
                    amount=round(random.uniform(100, 500), 2),
                    type=IncomeType.investment,
                    frequency=Frequency.monthly
                ))
            
            total_period_income = sum(source.amount for source in sources)
            
            periods.append(IncomeEntry(
                period=period_id,
                periodStart=current_date,
                periodEnd=period_end,
                totalIncome=round(total_period_income, 2),
                sources=sources
            ))
            
            current_date = period_end
        
        # Calculate aggregated data
        total_income = sum(entry.totalIncome for entry in periods)
        average_income = total_income / len(periods) if periods else 0
        
        # Calculate growth rate (mock) - use seeded random for consistency
        random.seed(seed_value + 999)
        income_growth = round(random.uniform(-0.05, 0.15), 3)
        
        # Calculate stability (mock) - use seeded random for consistency
        random.seed(seed_value + 1000)
        income_stability = round(random.uniform(0.7, 0.95), 2)
        
        return IncomeResponse(
            userId=user_id,
            startDate=start_date,
            endDate=end_date,
            granularity=granularity,
            totalIncome=round(total_income, 2),
            averageIncome=round(average_income, 2),
            incomeEntries=periods,
            incomeGrowth=income_growth,
            incomeStability=income_stability
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

@app.get("/api/v1/users/{user_id}/products", response_model=UserProductsResponse)
async def get_user_products(
    user_id: str = Path(..., description="The user's unique identifier"),
    _: str = Depends(verify_token)
) -> UserProductsResponse:
    """
    Get user products and subscriptions
    
    Args:
        user_id: User's unique identifier
        
    Returns:
        User products response with list of products and subscription details
        
    Raises:
        HTTPException: If user not found or other error occurs
    """
    try:
        logger.info(f"Retrieving products for user: {user_id}")
        
        # Generate mock data for any user ID
        result = MockDataGenerator.generate_user_products(user_id)
        
        logger.info(f"Retrieved {len(result.products)} products for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving products for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=ErrorDetails(
                    code=ErrorCode.INTERNAL_ERROR,
                    details=f"Failed to retrieve products: {str(e)}"
                )
            ).dict()
        )

@app.get("/api/v1/users/{user_id}/financial-score", response_model=FinancialScoreResponse)
async def get_user_financial_score(
    user_id: str = Path(..., description="The user's unique identifier"),
    score_type: ScoreType = Query(ScoreType.composite, description="Type of financial score to retrieve"),
    _: str = Depends(verify_token)
) -> FinancialScoreResponse:
    """
    Get user financial score
    
    Args:
        user_id: User's unique identifier
        score_type: Type of financial score to retrieve
        
    Returns:
        Financial score response with score details and contributing factors
        
    Raises:
        HTTPException: If user not found or invalid score type
    """
    try:
        logger.info(f"Retrieving {score_type.value} financial score for user: {user_id}")
        
        # Generate mock data for any user ID
        result = MockDataGenerator.generate_financial_score(user_id, score_type)
        
        logger.info(f"Retrieved {score_type.value} score of {result.score} for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving financial score for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=ErrorDetails(
                    code=ErrorCode.INTERNAL_ERROR,
                    details=f"Failed to retrieve financial score: {str(e)}"
                )
            ).dict()
        )

@app.get("/api/v1/users/{user_id}/income", response_model=IncomeResponse)
async def get_user_income(
    user_id: str = Path(..., description="The user's unique identifier"),
    startDate: datetime = Query(..., description="Start date for income period (ISO 8601 format)"),
    endDate: datetime = Query(..., description="End date for income period (ISO 8601 format)"),
    granularity: Granularity = Query(Granularity.monthly, description="Aggregation granularity"),
    _: str = Depends(verify_token)
) -> IncomeResponse:
    """
    Get user income data
    
    Args:
        user_id: User's unique identifier
        startDate: Start date for income period
        endDate: End date for income period
        granularity: Aggregation granularity
        
    Returns:
        Income response with aggregated income data
        
    Raises:
        HTTPException: If user not found or invalid date range
    """
    try:
        logger.info(f"Retrieving income data for user: {user_id} from {startDate} to {endDate}")
        
        # Validate date range
        if startDate >= endDate:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error=ErrorDetails(
                        code=ErrorCode.INVALID_DATE_RANGE,
                        details="Start date must be before end date"
                    )
                ).dict()
            )
        
        # Generate mock data for any user ID
        result = MockDataGenerator.generate_income_data(user_id, startDate, endDate, granularity)
        
        logger.info(f"Retrieved income data with {len(result.incomeEntries)} entries for user {user_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving income data for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=ErrorDetails(
                    code=ErrorCode.INTERNAL_ERROR,
                    details=f"Failed to retrieve income data: {str(e)}"
                )
            ).dict()
        )

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
