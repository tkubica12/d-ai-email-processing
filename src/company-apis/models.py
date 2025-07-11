"""
Pydantic models for Company APIs service

This module defines all the data models used by the Company APIs service,
including request/response schemas and enums.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


class ProductType(str, Enum):
    """Product category enumeration"""
    banking = "banking"
    insurance = "insurance"
    investment = "investment"
    loan = "loan"
    credit = "credit"
    other = "other"


class ProductStatus(str, Enum):
    """Product status enumeration"""
    active = "active"
    inactive = "inactive"
    suspended = "suspended"
    pending = "pending"


class ScoreType(str, Enum):
    """Financial score type enumeration"""
    composite = "composite"
    creditworthiness = "creditworthiness"
    liquidity = "liquidity"
    stability = "stability"
    growth = "growth"


class Impact(str, Enum):
    """Score factor impact enumeration"""
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class IncomeType(str, Enum):
    """Income type enumeration"""
    salary = "salary"
    bonus = "bonus"
    commission = "commission"
    freelance = "freelance"
    investment = "investment"
    rental = "rental"
    other = "other"


class Frequency(str, Enum):
    """Income frequency enumeration"""
    one_time = "one-time"
    weekly = "weekly"
    bi_weekly = "bi-weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    annually = "annually"


class Granularity(str, Enum):
    """Income aggregation granularity enumeration"""
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class ErrorCode(str, Enum):
    """Error code enumeration"""
    USER_NOT_FOUND = "USER_NOT_FOUND"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    INVALID_SCORE_TYPE = "INVALID_SCORE_TYPE"
    INVALID_GRANULARITY = "INVALID_GRANULARITY"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class Product(BaseModel):
    """Product model representing a user's product or service"""
    
    id: str = Field(..., description="Unique product identifier", example="prod_123456")
    name: str = Field(..., description="Product name", example="Premium Banking Package")
    type: ProductType = Field(..., description="Product category", example=ProductType.banking)
    status: ProductStatus = Field(..., description="Current product status", example=ProductStatus.active)
    monthlyFee: float = Field(..., ge=0, description="Monthly fee for the product", example=29.99)
    startDate: datetime = Field(..., description="Product subscription start date")
    endDate: Optional[datetime] = Field(None, description="Product subscription end date (if applicable)")
    features: List[str] = Field(
        ..., 
        description="List of product features",
        example=["Unlimited transactions", "24/7 customer support", "Mobile banking app"]
    )


class UserProductsResponse(BaseModel):
    """Response model for user products endpoint"""
    
    userId: str = Field(..., description="The user's unique identifier", example="john.doe@example.com")
    products: List[Product] = Field(..., description="List of user's active products and services")
    totalActiveSubscriptions: int = Field(
        ..., 
        ge=0, 
        description="Total number of active subscriptions", 
        example=2
    )
    totalMonthlyFees: float = Field(
        ..., 
        ge=0, 
        description="Total monthly fees for all subscriptions", 
        example=79.98
    )


class ScoreFactor(BaseModel):
    """Model representing a factor contributing to the financial score"""
    
    name: str = Field(..., description="Name of the scoring factor", example="Debt-to-Income Ratio")
    value: float = Field(..., description="Current value of the factor", example=0.35)
    weight: float = Field(
        ..., 
        ge=0, 
        le=1, 
        description="Weight of this factor in overall score (0-1)", 
        example=0.25
    )
    impact: Impact = Field(..., description="Impact of this factor on the score", example=Impact.negative)
    description: Optional[str] = Field(
        None, 
        description="Description of the factor",
        example="Current debt payments represent 35% of monthly income"
    )


class FinancialScoreResponse(BaseModel):
    """Response model for financial score endpoint"""
    
    userId: str = Field(..., description="The user's unique identifier", example="john.doe@example.com")
    scoreType: ScoreType = Field(..., description="Type of financial score", example=ScoreType.composite)
    score: int = Field(..., ge=0, le=100, description="Financial score value", example=82)
    maxScore: int = Field(..., description="Maximum possible score", example=100)
    scoreDate: datetime = Field(..., description="Date when the score was calculated")
    factors: List[ScoreFactor] = Field(..., description="Factors contributing to the score")
    recommendations: List[str] = Field(
        ..., 
        description="Recommendations for improving the score",
        example=[
            "Consider increasing monthly savings contributions",
            "Explore debt consolidation options to improve debt-to-income ratio"
        ]
    )


class IncomeSource(BaseModel):
    """Model representing an income source"""
    
    source: str = Field(..., description="Name of the income source", example="Acme Corp Salary")
    amount: float = Field(..., ge=0, description="Amount from this source", example=5500.00)
    type: IncomeType = Field(..., description="Type of income", example=IncomeType.salary)
    frequency: Optional[Frequency] = Field(None, description="Frequency of this income", example=Frequency.monthly)


class IncomeEntry(BaseModel):
    """Model representing income data for a specific period"""
    
    period: str = Field(..., description="Period identifier", example="2025-01")
    periodStart: datetime = Field(..., description="Start date of the period")
    periodEnd: datetime = Field(..., description="End date of the period")
    totalIncome: float = Field(..., ge=0, description="Total income for this period", example=6000.00)
    sources: List[IncomeSource] = Field(..., description="Income sources for this period")


class IncomeResponse(BaseModel):
    """Response model for income endpoint"""
    
    userId: str = Field(..., description="The user's unique identifier", example="john.doe@example.com")
    startDate: datetime = Field(..., description="Start date of the income period")
    endDate: datetime = Field(..., description="End date of the income period")
    granularity: Granularity = Field(..., description="Aggregation granularity used", example=Granularity.monthly)
    totalIncome: float = Field(..., ge=0, description="Total income for the period", example=42000.00)
    averageIncome: float = Field(..., ge=0, description="Average income per period", example=6000.00)
    incomeEntries: List[IncomeEntry] = Field(..., description="Individual income entries for each period")
    incomeGrowth: float = Field(..., description="Income growth rate (as decimal percentage)", example=0.05)
    incomeStability: float = Field(
        ..., 
        ge=0, 
        le=1, 
        description="Income stability score (0-1, where 1 is most stable)", 
        example=0.88
    )


class ErrorDetails(BaseModel):
    """Error details model"""
    
    code: ErrorCode = Field(..., description="Error code", example=ErrorCode.USER_NOT_FOUND)
    details: str = Field(
        ..., 
        description="Detailed error message",
        example="User with ID 'john.doe@example.com' was not found in the system"
    )


class ErrorResponse(BaseModel):
    """Error response model"""
    
    error: ErrorDetails = Field(..., description="Error details")
