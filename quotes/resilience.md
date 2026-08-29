# Resilience & Setback

- **Core Principles**: [[resilience]] · [[patience]] · [[kaizen]]
- **Session Moments**: bug-found · bug-fixed · tests-failing/setback
- **Tech Mappings**: [[testing-strategy]] · [[micro-saas-architecture]] · [[api-contract-design]]

> "Smooth seas do not make skillful sailors." — African proverb

> "Every problem is a gift — without problems we would not grow." — [[Anthony Robbins]]

> "A gem cannot be polished without friction, nor a man perfected without trials." — [[Seneca]]

> "Life's challenges are not supposed to paralyze you; they're supposed to help you discover who you are." — [[Bernice Johnson Reagon]]

> "Difficulties are things that show a person what they are." — [[Epictetus]] (*Discourses*)

> "When one door of happiness closes, another opens." — [[Helen Keller]]

> "There is no education like adversity." — [[Benjamin Disraeli]]

> "The cave you fear to enter holds the treasure you seek." — [[Joseph Campbell]]

> "Usipoziba ufa, utajenga ukuta." (If you don't seal the crack, you'll rebuild the wall.) — Swahili proverb

> "The greater the obstacle, the more glory in overcoming it." — [[Molière]]

> "Fall seven times, stand up eight." — Japanese proverb (Nana korobi ya oki)

> "What lies behind us and what lies before us are tiny matters compared to what lies within us." — attributed to [[Ralph Waldo Emerson]]

> "Out of difficulties grow miracles." — [[Jean de La Bruyère]]

> "Baada ya dhiki, faraja." (After hardship comes relief.) — Swahili proverb

> "Difficulties strengthen the mind, as labor does the body." — [[Seneca]]

> "The wound is the place where the Light enters you." — [[Rumi]]

> "Turn your wounds into wisdom." — [[Oprah Winfrey]]

> "He conquers who endures." — [[Persius]]

> "Strength does not come from winning. Your struggles develop your strengths." — [[Arnold Schwarzenegger]]

> "That which does not kill us makes us stronger." — [[Friedrich Nietzsche]]

> "Victory belongs to the most persevering." — attributed to [[Napoleon Bonaparte]]

> "Our greatest glory is not in never falling, but in rising every time we fall." — [[Confucius]]

> "It is not because things are difficult that we do not dare; it is because we do not dare that things are difficult." — [[Seneca]]

> "Every adversity carries with it the seed of an equal or greater benefit." — [[Napoleon Hill]]

> "The bamboo that bends is stronger than the oak that resists." — Japanese proverb

> "Failure is simply the opportunity to begin again, this time more intelligently." — [[Henry Ford]]

> "When we are no longer able to change a situation, we are challenged to change ourselves." — [[Viktor Frankl]] (*Man's Search for Meaning*)

> "I have not failed. I've just found 10,000 ways that won't work." — [[Thomas Edison]]

> "Ever tried. Ever failed. No matter. Try again. Fail again. Fail better." — [[Samuel Beckett]]

> "Do not judge me by my successes, judge me by how many times I fell down and got back up again." — [[Nelson Mandela]]

> "The greatest test of courage on earth is to bear defeat without losing heart." — [[Robert Green Ingersoll]]

> "It always seems impossible until it's done." — [[Nelson Mandela]]

## Code Directive

Design for graceful degradation and fast recovery. Treat each failure as data
for the next attempt — add a test or guard so the class of failure cannot recur
silently.
