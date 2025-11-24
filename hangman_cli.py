#!/usr/bin/env python3
"""
Hangman game that uses Gemini API to get a random word.
The game logic is hardcoded.
"""

from __future__ import annotations

import argparse
import sys
from typing import Set


def get_client():
    try:
        from google import genai
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise SystemExit(
            "Missing dependency 'google-genai'. Install it with 'pip install google-genai'."
        ) from exc
    return genai.Client()


def get_random_word(client, model: str, difficulty: str = "medium") -> str:
    """Request a random word from Gemini API."""
    difficulty_hint = {
        "easy": "a simple word between 4-6 letters",
        "medium": "a word between 5-8 letters",
        "hard": "a challenging word between 7-12 letters"
    }.get(difficulty, "a word between 5-8 letters")
    
    prompt = f"""Give me a single random {difficulty_hint} for a hangman game. 
Return ONLY the word itself, nothing else. No explanations, no quotes, no punctuation. 
Just the word in lowercase letters."""
    
    response = client.models.generate_content(model=model, contents=prompt)
    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")
    
    # Clean the response - remove quotes, whitespace, and convert to lowercase
    word = response.text.strip().strip('"').strip("'").lower()
    # Remove any non-alphabetic characters
    word = ''.join(c for c in word if c.isalpha())
    
    if not word:
        raise RuntimeError("Gemini did not return a valid word.")
    
    return word


def get_fun_statement(client, model: str, letter: str, is_correct: bool, wrong_guesses: int, max_wrong: int) -> str:
    """Get a weird, fun statement from Gemini based on whether the guess was correct or incorrect."""
    if is_correct:
        prompt = f"""The player just guessed the letter '{letter}' correctly in a hangman game. 
Generate a weird, fun, and entertaining one-sentence statement celebrating this correct guess. 
Be creative, quirky, and make it memorable! Keep it under 100 characters. 
Return ONLY the statement, no quotes, no explanations."""
    else:
        remaining = max_wrong - wrong_guesses
        prompt = f"""The player just guessed the letter '{letter}' incorrectly in a hangman game. 
They have {remaining} wrong guesses remaining out of {max_wrong} total.
Generate a weird, fun, and entertaining one-sentence statement about this wrong guess. 
Be creative, quirky, and make it memorable! Keep it under 100 characters.
Return ONLY the statement, no quotes, no explanations."""
    
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        if response.text:
            statement = response.text.strip().strip('"').strip("'")
            return statement
    except Exception:
        pass  # Fall back to default messages if API call fails
    
    # Fallback messages if Gemini fails
    if is_correct:
        return f"🎯 Nice! '{letter}' is definitely hanging out in that word!"
    else:
        return f"😅 Oops! '{letter}' is taking a vacation from this word!"




def display_word(word: str, guessed_letters: Set[str]) -> str:
    """Display the word with blanks for unguessed letters."""
    return ' '.join(letter if letter in guessed_letters else '_' for letter in word)


def display_hangman(wrong_guesses: int) -> str:
    """Display ASCII art hangman based on wrong guesses."""
    stages = [
        """
           +---+
           |   |
               |
               |
               |
               |
         =========
        """,
        """
           +---+
           |   |
           O   |
               |
               |
               |
         =========
        """,
        """
           +---+
           |   |
           O   |
           |   |
               |
               |
         =========
        """,
        """
           +---+
           |   |
           O   |
          /|   |
               |
               |
         =========
        """,
        """
           +---+
           |   |
           O   |
          /|\\  |
               |
               |
         =========
        """,
        """
           +---+
           |   |
           O   |
          /|\\  |
          /    |
               |
         =========
        """,
        """
           +---+
           |   |
           O   |
          /|\\  |
          / \\  |
               |
         =========
        """
    ]
    return stages[min(wrong_guesses, len(stages) - 1)]


def play_hangman(word: str, client, model: str) -> bool:
    """Main game loop. Returns True if player wins, False if loses."""
    guessed_letters: Set[str] = set()
    wrong_guesses = 0
    max_wrong_guesses = 6
    
    print("\n" + "="*50)
    print("Welcome to Hangman!")
    print("="*50)
    print(f"\nThe word has {len(word)} letters.")
    print(display_word(word, guessed_letters))
    print()
    
    while wrong_guesses < max_wrong_guesses:
        # Get user input
        guess = input("Guess a letter: ").strip().lower()
        
        # Validate input
        if not guess:
            print("Please enter a letter.")
            continue
        
        if len(guess) != 1:
            print("Please enter only one letter at a time.")
            continue
        
        if not guess.isalpha():
            print("Please enter a valid letter (a-z).")
            continue
        
        if guess in guessed_letters:
            print(f"You already guessed '{guess}'. Try a different letter.")
            continue
        
        guessed_letters.add(guess)
        
        # Check if guess is correct
        is_correct = guess in word
        if is_correct:
            fun_statement = get_fun_statement(client, model, guess, True, wrong_guesses, max_wrong_guesses)
            print(f"\n✨ {fun_statement}")
        else:
            wrong_guesses += 1
            fun_statement = get_fun_statement(client, model, guess, False, wrong_guesses, max_wrong_guesses)
            print(f"\n💭 {fun_statement}")
            print(f"Wrong guesses remaining: {max_wrong_guesses - wrong_guesses}")
        
        # Display current state
        current_display = display_word(word, guessed_letters)
        print(f"\nWord: {current_display}")
        print(display_hangman(wrong_guesses))
        
        # Check for win condition
        if all(letter in guessed_letters for letter in word):
            print("\n" + "="*50)
            print("🎉 Congratulations! You won!")
            print(f"The word was: {word.upper()}")
            print("="*50)
            return True
        
        # Check for lose condition
        if wrong_guesses >= max_wrong_guesses:
            print("\n" + "="*50)
            print("💀 Game Over! You ran out of guesses.")
            print(f"The word was: {word.upper()}")
            print("="*50)
            return False
        
        print()
    
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hangman game powered by Gemini API. Get a random word and play!"
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default="medium",
        help="Difficulty level: easy (4-6 letters), medium (5-8 letters), hard (7-12 letters).",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
        help="Gemini model to use (default: gemini-2.0-flash).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = get_client()
    
    try:
        print("Fetching a random word from Gemini...")
        word = get_random_word(client, args.model, args.difficulty)
        play_hangman(word, client, args.model)
    except KeyboardInterrupt:
        sys.exit("\n\nGame cancelled by user.")
    except Exception as e:
        sys.exit(f"\nError: {e}")


if __name__ == "__main__":
    main()

