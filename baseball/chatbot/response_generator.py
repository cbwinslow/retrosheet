"""Response generation for chatbot.

Generates natural language responses based on intent,
entities, and query results.

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import random
from typing import Dict, List, Any, Optional
from datetime import datetime


class ResponseGenerator:
    """Generate natural language responses.
    
    Creates contextually appropriate responses based on:
    - Intent type
    - Query results
    - Conversation context
    - User preferences
    
    Example:
        >>> generator = ResponseGenerator()
        >>> result = {'win_probability': 0.65, 'team': 'NYY'}
        >>> response = generator.generate_prediction_response(result)
        >>> print(response)  # "The Yankees have a 65% chance of winning..."
    """
    
    # Response templates
    GREETINGS = [
        "Hey there! Ready to talk some baseball?",
        "Hello! What would you like to know about today's games?",
        "Hi! I'm your baseball prediction assistant. What can I help you with?",
        "Welcome! Ask me about win probabilities, player stats, or game info.",
    ]
    
    HELP_MESSAGES = [
        """I can help you with:
        • Win probabilities and predictions
        • Player statistics (batting average, ERA, OPS, etc.)
        • Game information and schedules
        • Team standings
        • Player comparisons
        
        Try asking: "What's the Yankees win probability?" or "How is Judge doing?""",
        
        """Here are some things you can ask me:
        - "Will the Dodgers win today?"
        - "What's Ohtani's batting average?"
        - "Where are the Red Sox in the standings?"
        - "When do the Cubs play next?"
        
        What would you like to know?""",
    ]
    
    UNKNOWN_RESPONSES = [
        "I'm not sure I understood that. Could you rephrase?",
        "Hmm, I didn't catch that. Try asking about a specific team or player.",
        "I can help with baseball predictions and stats. What team are you interested in?",
    ]
    
    CLARIFICATION_PROMPTS = [
        "Which team are you asking about?",
        "Could you tell me which player you're interested in?",
        "Which game would you like to know about?",
    ]
    
    def __init__(self):
        """Initialize response generator."""
        pass
    
    def generate(self, intent_type: str, result: Optional[Dict],
                context: Optional[Dict] = None) -> str:
        """Generate response based on intent and result.
        
        Args:
            intent_type: Type of intent
            result: Query result data
            context: Conversation context
            
        Returns:
            Natural language response
        """
        context = context or {}
        
        if intent_type == 'greeting':
            return self._generate_greeting()
        elif intent_type == 'help':
            return self._generate_help()
        elif intent_type == 'prediction':
            return self._generate_prediction_response(result, context)
        elif intent_type == 'game_info':
            return self._generate_game_info_response(result, context)
        elif intent_type == 'player_stats':
            return self._generate_player_stats_response(result, context)
        elif intent_type == 'standings':
            return self._generate_standings_response(result, context)
        elif intent_type == 'schedule':
            return self._generate_schedule_response(result, context)
        elif intent_type == 'comparison':
            return self._generate_comparison_response(result, context)
        elif intent_type == 'explanation':
            return self._generate_explanation_response(result, context)
        else:
            return self._generate_unknown_response()
    
    def _generate_greeting(self) -> str:
        """Generate greeting response."""
        return random.choice(self.GREETINGS)
    
    def _generate_help(self) -> str:
        """Generate help message."""
        return random.choice(self.HELP_MESSAGES)
    
    def _generate_prediction_response(self, result: Optional[Dict],
                                    context: Dict) -> str:
        """Generate response for prediction intent."""
        if not result:
            return "I don't have a prediction available for that right now."
        
        pred_type = result.get('prediction_type', 'win')
        team = result.get('team', 'the team')
        probability = result.get('probability', 0.5)
        
        if pred_type == 'win_probability':
            prob_pct = probability * 100
            if prob_pct > 60:
                return f"{team} are looking strong with a {prob_pct:.0f}% chance of winning!"
            elif prob_pct < 40:
                return f"{team} are the underdogs right now with a {prob_pct:.0f}% win probability."
            else:
                return f"It's a close game! {team} have a {prob_pct:.0f}% chance of winning."
        
        elif pred_type == 'run_probability':
            prob_pct = probability * 100
            return f"There's a {prob_pct:.0f}% chance of a run scoring in this situation."
        
        elif pred_type == 'pa_outcome':
            outcomes = result.get('outcomes', {})
            most_likely = max(outcomes, key=outcomes.get)
            prob = outcomes[most_likely] * 100
            return f"The most likely outcome is a {most_likely} ({prob:.0f}% probability)."
        
        return f"Based on my analysis, the probability is {probability*100:.1f}%."
    
    def _generate_game_info_response(self, result: Optional[Dict],
                                   context: Dict) -> str:
        """Generate response for game info intent."""
        if not result:
            return "I don't have information about that game right now."
        
        info_type = result.get('info_type', 'general')
        
        if info_type == 'score':
            home_team = result.get('home_team', 'Home')
            away_team = result.get('away_team', 'Away')
            home_score = result.get('home_score', 0)
            away_score = result.get('away_score', 0)
            inning = result.get('inning', '?')
            return f"{away_team} {away_score}, {home_team} {home_score} (bottom {inning})"
        
        elif info_type == 'pitching':
            pitcher = result.get('pitcher', 'Unknown')
            era = result.get('era', '?')
            return f"{pitcher} is on the mound with a {era} ERA."
        
        elif info_type == 'lineup':
            return "The lineup features their usual starters. Who would you like to know about?"
        
        return f"Game info: {str(result)}"
    
    def _generate_player_stats_response(self, result: Optional[Dict],
                                    context: Dict) -> str:
        """Generate response for player stats intent."""
        if not result:
            player = context.get('active_player', 'the player')
            return f"I don't have stats available for {player} right now."
        
        player = result.get('player_name', 'the player')
        stat_type = result.get('stat_type', 'general')
        value = result.get('value', '?')
        
        stat_descriptions = {
            'batting_average': f"{player} is hitting {value}",
            'era': f"{player} has a {value} ERA",
            'ops': f"{player}'s OPS is {value}",
            'war': f"{player} has accumulated {value} WAR",
            'home_runs': f"{player} has {value} home runs",
            'rbis': f"{player} has {value} RBIs",
        }
        
        if stat_type in stat_descriptions:
            return stat_descriptions[stat_type]
        
        return f"{player}'s {stat_type}: {value}"
    
    def _generate_standings_response(self, result: Optional[Dict],
                                  context: Dict) -> str:
        """Generate response for standings intent."""
        if not result:
            team = context.get('active_team', 'the team')
            return f"I don't have current standings for {team}."
        
        team = result.get('team', 'the team')
        position = result.get('position', '?')
        games_back = result.get('games_back', 0)
        wins = result.get('wins', 0)
        losses = result.get('losses', 0)
        
        if games_back == 0:
            return f"{team} are in 1st place with a {wins}-{losses} record!"
        elif games_back <= 3:
            return f"{team} are {position} place, just {games_back} games back at {wins}-{losses}."
        else:
            return f"{team} are in {position} place, {games_back} games back with a {wins}-{losses} record."
    
    def _generate_schedule_response(self, result: Optional[Dict],
                                 context: Dict) -> str:
        """Generate response for schedule intent."""
        if not result:
            team = context.get('active_team', 'that team')
            return f"I don't have schedule information for {team} right now."
        
        team = result.get('team', 'the team')
        opponent = result.get('opponent', 'TBD')
        game_date = result.get('date', 'soon')
        time = result.get('time', 'TBD')
        location = result.get('location', 'home')
        
        loc_text = "at home" if location == 'home' else f"at {opponent}"
        return f"{team} play {opponent} {loc_text} on {game_date} at {time}."
    
    def _generate_comparison_response(self, result: Optional[Dict],
                                   context: Dict) -> str:
        """Generate response for comparison intent."""
        if not result:
            return "I need more information to compare those players."
        
        player1 = result.get('player1', 'Player 1')
        player2 = result.get('player2', 'Player 2')
        stat = result.get('stat', 'the stat')
        p1_value = result.get('player1_value', 0)
        p2_value = result.get('player2_value', 0)
        
        if p1_value > p2_value:
            return f"{player1} has the edge in {stat} ({p1_value} vs {p2_value})."
        elif p2_value > p1_value:
            return f"{player2} is better in {stat} ({p2_value} vs {p1_value})."
        else:
            return f"They're pretty even in {stat} ({p1_value})."
    
    def _generate_explanation_response(self, result: Optional[Dict],
                                    context: Dict) -> str:
        """Generate response for explanation intent."""
        if not result:
            return """I calculate predictions using:
            
• Win Expectancy based on game state (score, inning, bases, outs)
• Leverage Index for clutch situation analysis
• Player matchup data and recent performance
• Bullpen strength and fatigue
• Historical patterns and context

The models are trained on thousands of historical games."""
        
        explanation = result.get('explanation', '')
        return explanation
    
    def _generate_unknown_response(self) -> str:
        """Generate response for unknown intent."""
        return random.choice(self.UNKNOWN_RESPONSES)
    
    def ask_clarification(self, missing: str) -> str:
        """Ask user for clarification.
        
        Args:
            missing: What's missing (team, player, game)
            
        Returns:
            Clarification prompt
        """
        if missing == 'team':
            return "Which team are you asking about?"
        elif missing == 'player':
            return "Which player would you like to know about?"
        elif missing == 'game':
            return "Which game are you interested in?"
        else:
            return random.choice(self.CLARIFICATION_PROMPTS)
    
    def format_prediction_details(self, prediction: Dict) -> str:
        """Format detailed prediction information.
        
        Args:
            prediction: Prediction result dictionary
            
        Returns:
            Formatted details string
        """
        lines = []
        
        if 'win_probability' in prediction:
            wp = prediction['win_probability'] * 100
            lines.append(f"Win Probability: {wp:.1f}%")
        
        if 'leverage_index' in prediction:
            li = prediction['leverage_index']
            if li > 2:
                lines.append(f"Leverage Index: {li:.2f} (High pressure situation)")
            elif li > 1:
                lines.append(f"Leverage Index: {li:.2f} (Above average pressure)")
            else:
                lines.append(f"Leverage Index: {li:.2f}")
        
        if 'key_factors' in prediction:
            lines.append("\nKey Factors:")
            for factor in prediction['key_factors'][:3]:
                lines.append(f"• {factor}")
        
        return '\n'.join(lines)
