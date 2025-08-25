from typing import List, Dict, Any
from utils.llm_client import OpenRouterClient
from domain.chapter import Chapter
from domain.adventure import Adventure


class StoryManager:
    """
    Manages story generation, LLM interactions, and narrative logic.
    Separated from game mechanics to focus purely on storytelling.
    """
    
    def __init__(self):
        self.llm_client = OpenRouterClient()

    async def generate_story_directions(self, story_state: List[Dict], adventure: Adventure, current_round: int) -> List[Dict]:
        """
        Generate story directions for all players based on their current state.
        
        Args:
            story_state: List of player states with their last chapters and choices
            adventure: The current adventure object
            current_round: Current round number
            
        Returns:
            List of direction objects with player_name and next_direction fields
        """
        planning_prompt = f"""
            Based on the current story state, create a plan for what direction each player's story should go next.
            Current round: {current_round}
            
            Players and their last actions:
            {story_state}
            
            Adventure: {adventure.title}
            {adventure.description}
            
            Map:
            {adventure.map.to_dict()}

            For each player, provide a brief direction (1-2 sentences) for what should happen next in their story.
            Return only a JSON array with objects containing 'player_name' and 'next_direction' fields.
            Make the directions engaging and build on their previous choices.
            
            Guidelines:
            - Create tension and mystery appropriate to the adventure theme
            - Reference specific map areas when relevant
            - Build on previous player choices to create continuity
            - Ensure each direction leads to meaningful choices
            - Vary the pacing - some players might face immediate danger, others discovery
        """
        
        print(f"[STORY] Generating story directions for {len(story_state)} players")
        
        response = await self.llm_client.chat_completion([
            {"role": "system", "content": "You are a master storyteller and game master. Create engaging, interconnected story directions that build narrative tension while respecting player agency."},
            {"role": "user", "content": planning_prompt}
        ])
        
        # Parse the response with robust JSON handling
        try:
            directions = self.llm_client.parse_json_response(
                response.content,
                fallback_value=[
                    {"player_name": player["player_name"], "next_direction": "Continue your adventure with new challenges ahead."}
                    for player in story_state
                ]
            )
            print(f"[STORY] Successfully generated {len(directions)} story directions")
            return directions
        except Exception as e:
            print(f"[STORY] Error parsing directions: {e}")
            # Return fallback directions
            return [
                {"player_name": player["player_name"], "next_direction": "Continue your adventure with new challenges ahead."}
                for player in story_state
            ]

    async def generate_chapter(self, player_name: str, story_direction: str, adventure: Adventure, 
                             previous_chapters: List[Chapter] = None, last_choice: str = None) -> Chapter:
        """
        Generate a single chapter for a specific player.
        
        Args:
            player_name: Name of the player
            story_direction: Direction from the story planning
            adventure: Current adventure
            previous_chapters: List of previous chapters for context
            last_choice: The player's last choice text
            
        Returns:
            Generated Chapter object
        """
        print(f"[STORY] Generating chapter for {player_name}")
        
        # Build context for the chapter generation
        story_context = self._build_story_context(
            player_name, story_direction, adventure, previous_chapters, last_choice
        )
        
        # Create the chapter generation prompt
        prompt = f"""Generate the next chapter for this {adventure.title} adventure.

        Create an immersive, atmospheric scene that fits the {self._get_adventure_genre(adventure)} setting. 
        
        The chapter should:
        - Be 2-4 sentences long and set an engaging mood
        - Reference specific areas from the adventure map when appropriate
        - Build tension and atmosphere appropriate to the genre
        - Lead naturally to meaningful player choices
        - Follow the story direction provided in the context
        - Continue seamlessly from the previous chapter if one exists
        
        Generate exactly 3 compelling choices that:
        - Offer different approaches to the situation
        - Have meaningful consequences
        - Allow for different player personalities/strategies
        - Advance the story in different directions"""

        chapter = await self.llm_client.generate_chapter(
            prompt=prompt,
            context=story_context,
            num_choices=3
        )
        
        print(f"[STORY] Generated chapter for {player_name}: {len(chapter.text)} chars, {len(chapter.possiblities)} choices")
        return chapter

    def _build_story_context(self, player_name: str, story_direction: str, adventure: Adventure, 
                           previous_chapters: List[Chapter] = None, last_choice: str = None) -> str:
        """Build comprehensive story context for chapter generation."""
        
        context_parts = [
            f"Adventure: {adventure.title}",
            f"Setting: {adventure.description}",
            f"Player: {player_name}",
            f"Story Direction: {story_direction}",
        ]
        
        # Add previous chapter context if available
        if previous_chapters:
            last_chapter = previous_chapters[-1]
            context_parts.extend([
                "",
                "Previous Chapter:",
                last_chapter.text,
                f"Player's Last Choice: {last_choice or 'No choice made yet'}"
            ])
            
            # Add recent history context (last 2-3 chapters)
            if len(previous_chapters) > 1:
                recent_chapters = previous_chapters[-3:-1]  # Skip the last one (already included)
                context_parts.extend([
                    "",
                    "Recent Story History:",
                    *[f"- {ch.text}" for ch in recent_chapters]
                ])
        else:
            context_parts.extend([
                "",
                "This is the beginning of the adventure. The player is starting their journey."
            ])
        
        # Add map information
        context_parts.extend([
            "",
            "Available Areas:",
            *[f"- {area.name}: {area.description}" for area in adventure.map.areas],
            "",
            "Area Connections:",
            *[f"- {area.name} connects to: {', '.join([adventure.map.areas[conn_id].name for conn_id in adventure.map.get_connected_areas(area.id)])}"
              for area in adventure.map.areas if adventure.map.get_connected_areas(area.id)]
        ])
        
        return "\n".join(context_parts)

    def _get_adventure_genre(self, adventure: Adventure) -> str:
        """Determine the genre/mood of the adventure based on its content."""
        title_lower = adventure.title.lower()
        desc_lower = adventure.description.lower()
        
        # Simple genre detection based on keywords
        if any(word in title_lower or word in desc_lower for word in ['haunted', 'ghost', 'horror', 'dark', 'cursed', 'evil']):
            return "horror/mystery"
        elif any(word in title_lower or word in desc_lower for word in ['space', 'starship', 'alien', 'sci-fi', 'future']):
            return "science fiction"
        elif any(word in title_lower or word in desc_lower for word in ['fantasy', 'magic', 'dragon', 'wizard', 'medieval']):
            return "fantasy"
        elif any(word in title_lower or word in desc_lower for word in ['adventure', 'treasure', 'exploration']):
            return "adventure"
        else:
            return "adventure"

    async def generate_narrative_summary(self, all_chapters: Dict[str, List[Chapter]], adventure: Adventure) -> str:
        """
        Generate a narrative summary of the adventure so far for all players.
        Useful for recap or story continuity.
        
        Args:
            all_chapters: Dictionary mapping player names to their chapter lists
            adventure: Current adventure
            
        Returns:
            A narrative summary of the adventure progress
        """
        summary_prompt = f"""
        Create a compelling narrative summary of this {adventure.title} adventure so far.
        
        Adventure: {adventure.title}
        Setting: {adventure.description}
        
        Player Stories:
        """
        
        for player_name, chapters in all_chapters.items():
            if chapters:
                summary_prompt += f"\n{player_name}:\n"
                for i, chapter in enumerate(chapters):
                    choice_text = ""
                    if chapter.choice != -1 and chapter.choice < len(chapter.possiblities):
                        choice_text = f" (chose: {chapter.possiblities[chapter.choice]})"
                    summary_prompt += f"  Chapter {i+1}: {chapter.text}{choice_text}\n"
        
        summary_prompt += """
        
        Write a cohesive narrative summary (3-4 paragraphs) that:
        - Captures the key events and developments
        - Highlights interesting player choices and their consequences
        - Sets up the current state of the adventure
        - Maintains the atmosphere and tone of the adventure
        """
        
        response = await self.llm_client.chat_completion([
            {"role": "system", "content": "You are a skilled narrator who weaves individual player stories into compelling adventure narratives."},
            {"role": "user", "content": summary_prompt}
        ])
        
        return response.content

    async def validate_story_consistency(self, player_chapters: List[Chapter], adventure: Adventure) -> Dict[str, Any]:
        """
        Analyze story consistency and provide suggestions for improvement.
        
        Args:
            player_chapters: List of chapters for a single player
            adventure: Current adventure
            
        Returns:
            Dictionary with consistency analysis and suggestions
        """
        if not player_chapters:
            return {"status": "no_chapters", "suggestions": []}
        
        analysis_prompt = f"""
        Analyze the story consistency for this player's adventure progression:
        
        Adventure: {adventure.title}
        Setting: {adventure.description}
        
        Player's Story Chapters:
        """
        
        for i, chapter in enumerate(player_chapters):
            choice_text = ""
            if chapter.choice != -1 and chapter.choice < len(chapter.possiblities):
                choice_text = f" → {chapter.possiblities[chapter.choice]}"
            analysis_prompt += f"\nChapter {i+1}: {chapter.text}{choice_text}"
        
        analysis_prompt += """
        
        Analyze this story for:
        1. Narrative consistency and flow
        2. Character development and growth
        3. Logical progression of events
        4. Appropriate pacing and tension
        5. Adherence to the adventure setting
        
        Return a JSON object with:
        {
            "consistency_score": <1-10>,
            "strengths": ["list of story strengths"],
            "issues": ["list of potential issues"],
            "suggestions": ["list of improvement suggestions"]
        }
        """
        
        response = await self.llm_client.chat_completion([
            {"role": "system", "content": "You are a professional story editor analyzing narrative consistency and quality."},
            {"role": "user", "content": analysis_prompt}
        ])
        
        try:
            return self.llm_client.parse_json_response(
                response.content,
                fallback_value={
                    "consistency_score": 7,
                    "strengths": ["Story progresses logically"],
                    "issues": [],
                    "suggestions": ["Continue developing the narrative"]
                }
            )
        except:
            return {
                "consistency_score": 7,
                "strengths": ["Story progresses logically"],
                "issues": [],
                "suggestions": ["Continue developing the narrative"]
            }
