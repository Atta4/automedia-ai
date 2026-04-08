"""
Hook Library - Collection of proven viral hook templates.
"""

import random
from typing import Dict, List, Optional
from datetime import datetime

from .models import HookFramework


class HookLibrary:
    """
    Library of proven viral hook templates.
    
    Each hook framework has multiple variations for content diversity.
    """
    
    # Hook templates by framework
    HOOK_TEMPLATES: Dict[HookFramework, List[str]] = {
        HookFramework.YOU_WONT_BELIEVE: [
            "You won't believe what just happened with {topic}.",
            "What I'm about to show you about {topic} will blow your mind.",
            "You've never seen anything like this {topic} story before.",
            "Wait until you hear what happened with {topic}.",
            "This {topic} situation is absolutely insane.",
        ],
        
        HookFramework.THE_TRUTH_ABOUT: [
            "The truth about {topic} that nobody wants to tell you.",
            "Here's what they're not telling you about {topic}.",
            "The real story behind {topic} that mainstream media won't cover.",
            "What nobody talks about regarding {topic}.",
            "The hidden truth about {topic} revealed.",
        ],
        
        HookFramework.WHAT_NOBODY_KNOWS: [
            "What nobody knows about {topic} will shock you.",
            "The {topic} secret that's been hiding in plain sight.",
            "There's something about {topic} they don't want you to know.",
            "The untold story of {topic} that changes everything.",
            "What I discovered about {topic} changed my perspective forever.",
        ],
        
        HookFramework.TOP_NUMBER: [
            "Top 3 secrets about {topic} that will change your life.",
            "The 5 biggest mistakes people make with {topic}.",
            "Top 7 {topic} hacks that actually work.",
            "3 {topic} truths that successful people know.",
            "The 5 most important things about {topic} you need to know.",
        ],
        
        HookFramework.NUMBER_WAYS: [
            "5 ways {topic} is changing everything right now.",
            "7 ways to master {topic} in record time.",
            "3 ways {topic} will impact your life today.",
            "10 ways successful people approach {topic}.",
            "4 ways to instantly improve your {topic} game.",
        ],
        
        HookFramework.NUMBER_MISTAKES: [
            "7 mistakes you're making with {topic} right now.",
            "The #1 mistake that's ruining your {topic} progress.",
            "5 {topic} mistakes that are costing you big time.",
            "3 critical {topic} errors everyone makes.",
            "Stop making these {topic} mistakes immediately.",
        ],
        
        HookFramework.STORY_BASED: [
            "Let me tell you the crazy story of {topic}.",
            "This is the incredible true story about {topic}.",
            "What happened with {topic} is something you have to hear.",
            "The {topic} story that has everyone talking.",
            "I never expected {topic} to lead to this...",
        ],
        
        HookFramework.PERSONAL_EXPERIENCE: [
            "When I first discovered {topic}, everything changed.",
            "My {topic} journey started exactly like yours.",
            "What I learned from {topic} shocked me to my core.",
            "I tried {topic} for 30 days and here's what happened.",
            "The {topic} mistake I made so you don't have to.",
        ],
        
        HookFramework.CASE_STUDY: [
            "How {topic} went from zero to hero.",
            "The {topic} strategy that generated millions.",
            "Case study: What {topic} teaches us about success.",
            "Breaking down the {topic} phenomenon step by step.",
            "The psychology behind why {topic} works so well.",
        ],
        
        HookFramework.WHY_QUESTION: [
            "Why is {topic} suddenly everywhere?",
            "Why does {topic} work so well?",
            "Why is nobody talking about {topic}?",
            "Why {topic} is the most important thing right now.",
            "Why everything you know about {topic} might be wrong.",
        ],
        
        HookFramework.HOW_QUESTION: [
            "How {topic} is changing the game forever.",
            "How to master {topic} in just minutes a day.",
            "How {topic} became a worldwide phenomenon.",
            "How I used {topic} to achieve the impossible.",
            "How {topic} works and why it matters to you.",
        ],
        
        HookFramework.WHAT_IF: [
            "What if everything you knew about {topic} was wrong?",
            "What if I told you {topic} is easier than you think?",
            "What if {topic} is the key to everything you want?",
            "What if the secret to success is just {topic}?",
            "What if {topic} could change your life in 24 hours?",
        ],
        
        HookFramework.PATTERN_INTERRUPT: [
            "Stop scrolling. This {topic} video is different.",
            "I need you to listen very carefully about {topic}.",
            "Pause. What you're about to see changes everything.",
            "Don't skip. This {topic} revelation is crucial.",
            "Wait. Before you scroll, you need to hear this about {topic}.",
        ],
        
        HookFramework.CONTROVERSIAL: [
            "{topic} is a complete lie and here's why.",
            "Everything you've been told about {topic} is wrong.",
            "Why {topic} is actually harming you.",
            "The uncomfortable truth about {topic}.",
            "I'm about to expose the {topic} industry scam.",
        ],
        
        HookFramework.URGENT_WARNING: [
            "Stop doing {topic} immediately until you watch this.",
            "Warning: What I'm about to reveal about {topic} is controversial.",
            "You need to hear this {topic} warning right now.",
            "Urgent {topic} update that affects everyone.",
            "Critical {topic} information you can't ignore.",
        ],
        
        HookFramework.THIS_IS_WHY: [
            "This is why you're not seeing results with {topic}.",
            "This is why {topic} works when nothing else does.",
            "This is why everyone is obsessed with {topic}.",
            "This is why {topic} is the future.",
            "This is why {topic} changed my entire life.",
        ],
        
        HookFramework.REASON_X: [
            "The #1 reason people fail at {topic}.",
            "The real reason {topic} works so well.",
            "The main reason you're struggling with {topic}.",
            "The surprising reason {topic} matters more than you think.",
            "The actual reason behind the {topic} phenomenon.",
        ],
        
        HookFramework.SECRET_TO: [
            "The secret to mastering {topic} revealed.",
            "The {topic} secret that changed everything for me.",
            "What successful people know about {topic} that you don't.",
            "The hidden secret behind effective {topic}.",
            "The one {topic} secret you need to know.",
        ],
    }
    
    # Hook duration recommendations (in seconds)
    HOOK_DURATIONS: Dict[HookFramework, tuple] = {
        HookFramework.YOU_WONT_BELIEVE: (2.5, 4),
        HookFramework.THE_TRUTH_ABOUT: (3, 5),
        HookFramework.WHAT_NOBODY_KNOWS: (3, 5),
        HookFramework.TOP_NUMBER: (3, 5),
        HookFramework.NUMBER_WAYS: (3, 5),
        HookFramework.NUMBER_MISTAKES: (3, 5),
        HookFramework.STORY_BASED: (4, 6),
        HookFramework.PERSONAL_EXPERIENCE: (4, 6),
        HookFramework.CASE_STUDY: (4, 6),
        HookFramework.WHY_QUESTION: (2.5, 4),
        HookFramework.HOW_QUESTION: (2.5, 4),
        HookFramework.WHAT_IF: (3, 5),
        HookFramework.PATTERN_INTERRUPT: (2, 3.5),
        HookFramework.CONTROVERSIAL: (3, 5),
        HookFramework.URGENT_WARNING: (2.5, 4),
        HookFramework.THIS_IS_WHY: (3, 5),
        HookFramework.REASON_X: (3, 5),
        HookFramework.SECRET_TO: (3, 5),
    }
    
    # Framework effectiveness by niche (0-100)
    NICHE_EFFECTIVENESS: Dict[str, Dict[HookFramework, float]] = {
        "motivation": {
            HookFramework.PERSONAL_EXPERIENCE: 90,
            HookFramework.THIS_IS_WHY: 85,
            HookFramework.TOP_NUMBER: 80,
            HookFramework.SECRET_TO: 85,
            HookFramework.STORY_BASED: 88,
        },
        "finance": {
            HookFramework.THE_TRUTH_ABOUT: 92,
            HookFramework.NUMBER_MISTAKES: 88,
            HookFramework.SECRET_TO: 90,
            HookFramework.CASE_STUDY: 85,
            HookFramework.THIS_IS_WHY: 82,
        },
        "ai_tech": {
            HookFramework.YOU_WONT_BELIEVE: 90,
            HookFramework.PATTERN_INTERRUPT: 88,
            HookFramework.WHAT_NOBODY_KNOWS: 85,
            HookFramework.HOW_QUESTION: 82,
            HookFramework.THIS_IS_WHY: 80,
        },
        "islamic": {
            HookFramework.STORY_BASED: 95,
            HookFramework.WHAT_NOBODY_KNOWS: 88,
            HookFramework.THE_TRUTH_ABOUT: 85,
            HookFramework.WHY_QUESTION: 82,
            HookFramework.PERSONAL_EXPERIENCE: 80,
        },
        "health_fitness": {
            HookFramework.NUMBER_MISTAKES: 90,
            HookFramework.THIS_IS_WHY: 88,
            HookFramework.TOP_NUMBER: 85,
            HookFramework.PERSONAL_EXPERIENCE: 82,
            HookFramework.SECRET_TO: 80,
        },
        "history": {
            HookFramework.STORY_BASED: 95,
            HookFramework.WHAT_NOBODY_KNOWS: 92,
            HookFramework.THE_TRUTH_ABOUT: 90,
            HookFramework.CASE_STUDY: 85,
            HookFramework.YOU_WONT_BELIEVE: 80,
        },
        "facts_did_you_know": {
            HookFramework.YOU_WONT_BELIEVE: 95,
            HookFramework.TOP_NUMBER: 92,
            HookFramework.WHAT_NOBODY_KNOWS: 90,
            HookFramework.NUMBER_WAYS: 85,
            HookFramework.PATTERN_INTERRUPT: 82,
        },
        "horror_stories": {
            HookFramework.STORY_BASED: 95,
            HookFramework.PATTERN_INTERRUPT: 90,
            HookFramework.WHAT_NOBODY_KNOWS: 88,
            HookFramework.THE_TRUTH_ABOUT: 85,
            HookFramework.YOU_WONT_BELIEVE: 82,
        },
        "relationships": {
            HookFramework.THIS_IS_WHY: 90,
            HookFramework.REASON_X: 88,
            HookFramework.THE_TRUTH_ABOUT: 85,
            HookFramework.NUMBER_MISTAKES: 82,
            HookFramework.WHY_QUESTION: 80,
        },
        "business": {
            HookFramework.CASE_STUDY: 92,
            HookFramework.SECRET_TO: 90,
            HookFramework.THIS_IS_WHY: 88,
            HookFramework.NUMBER_MISTAKES: 85,
            HookFramework.THE_TRUTH_ABOUT: 82,
        },
        "trending_viral": {
            HookFramework.PATTERN_INTERRUPT: 95,
            HookFramework.YOU_WONT_BELIEVE: 92,
            HookFramework.URGENT_WARNING: 90,
            HookFramework.THIS_IS_WHY: 85,
            HookFramework.WHAT_NOBODY_KNOWS: 82,
        },
        "current_affairs": {
            HookFramework.URGENT_WARNING: 92,
            HookFramework.THE_TRUTH_ABOUT: 90,
            HookFramework.THIS_IS_WHY: 88,
            HookFramework.PATTERN_INTERRUPT: 85,
            HookFramework.WHY_QUESTION: 82,
        },
    }
    
    @classmethod
    def get_hook(
        cls,
        framework: HookFramework,
        topic: str,
        variation_seed: Optional[int] = None
    ) -> str:
        """
        Get a hook template filled with the topic.
        
        Args:
            framework: Hook framework to use
            topic: Topic to insert into template
            variation_seed: Optional seed for variation
            
        Returns:
            Filled hook template
        """
        templates = cls.HOOK_TEMPLATES.get(framework, cls.HOOK_TEMPLATES[HookFramework.THIS_IS_WHY])
        
        if variation_seed is not None:
            # Deterministic selection based on seed
            random.seed(variation_seed)
        
        template = random.choice(templates)
        return template.format(topic=topic)
    
    @classmethod
    def get_best_framework_for_niche(
        cls,
        niche: str,
        topic: Optional[str] = None
    ) -> HookFramework:
        """
        Get the best hook framework for a niche.
        
        Args:
            niche: Niche identifier
            topic: Optional topic for topic-specific selection
            
        Returns:
            Best HookFramework for the niche
        """
        niche_lower = niche.lower()
        effectiveness_map = cls.NICHE_EFFECTIVENESS.get(niche_lower, {})
        
        if not effectiveness_map:
            # Default frameworks for unknown niches
            return HookFramework.THIS_IS_WHY
        
        # Get framework with highest effectiveness
        best_framework = max(effectiveness_map, key=effectiveness_map.get)
        return best_framework
    
    @classmethod
    def get_recommended_frameworks(
        cls,
        niche: str,
        top_n: int = 3
    ) -> List[HookFramework]:
        """
        Get top N recommended frameworks for a niche.
        
        Args:
            niche: Niche identifier
            top_n: Number of frameworks to return
            
        Returns:
            List of recommended HookFrameworks
        """
        niche_lower = niche.lower()
        effectiveness_map = cls.NICHE_EFFECTIVENESS.get(niche_lower, {})
        
        if not effectiveness_map:
            return [
                HookFramework.THIS_IS_WHY,
                HookFramework.PATTERN_INTERRUPT,
                HookFramework.STORY_BASED,
            ]
        
        # Sort by effectiveness and return top N
        sorted_frameworks = sorted(
            effectiveness_map.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [fw for fw, _ in sorted_frameworks[:top_n]]
    
    @classmethod
    def get_hook_duration(
        cls,
        framework: HookFramework
    ) -> tuple:
        """
        Get recommended duration range for a hook framework.
        
        Returns:
            Tuple of (min_duration, max_duration) in seconds
        """
        return cls.HOOK_DURATIONS.get(
            framework,
            (3, 5)  # Default duration
        )
    
    @classmethod
    def get_all_frameworks(cls) -> List[HookFramework]:
        """Get all available hook frameworks."""
        return list(cls.HOOK_TEMPLATES.keys())
    
    @classmethod
    def get_framework_description(cls, framework: HookFramework) -> str:
        """Get human-readable description of a hook framework."""
        descriptions = {
            HookFramework.YOU_WONT_BELIEVE: "Creates intense curiosity and anticipation",
            HookFramework.THE_TRUTH_ABOUT: "Reveals hidden information and secrets",
            HookFramework.WHAT_NOBODY_KNOWS: "Shares exclusive, unknown insights",
            HookFramework.TOP_NUMBER: "List-based format for easy consumption",
            HookFramework.NUMBER_WAYS: "Practical, actionable list format",
            HookFramework.NUMBER_MISTAKES: "Problem-awareness with solution promise",
            HookFramework.STORY_BASED: "Narrative-driven engagement",
            HookFramework.PERSONAL_EXPERIENCE: "Relatable first-person perspective",
            HookFramework.CASE_STUDY: "Evidence-based analysis",
            HookFramework.WHY_QUESTION: "Curiosity-driven question format",
            HookFramework.HOW_QUESTION: "Educational how-to format",
            HookFramework.WHAT_IF: "Hypothetical scenario engagement",
            HookFramework.PATTERN_INTERRUPT: "Breaks viewer expectations immediately",
            HookFramework.CONTROVERSIAL: "Challenges conventional wisdom",
            HookFramework.URGENT_WARNING: "Creates immediate urgency",
            HookFramework.THIS_IS_WHY: "Explains causes and reasons",
            HookFramework.REASON_X: "Identifies key factors",
            HookFramework.SECRET_TO: "Promises exclusive knowledge",
        }
        
        return descriptions.get(framework, "Effective hook framework")
