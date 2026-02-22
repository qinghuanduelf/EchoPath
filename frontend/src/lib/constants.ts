/**
 * Dropdown options for the student input form.
 * Mirror the constants from backend/config.py.
 */

export const EDUCATION_OPTIONS = [
    "High School",
    "Community College",
    "State University",
    "Flagship State University",
    "Private University",
    "Ivy League",
] as const;

export const FUNCTION_OPTIONS = [
    "Software Engineering",
    "Data Science",
    "Product Management",
    "Marketing",
    "Finance",
    "Consulting",
    "Design",
    "Sales",
    "Operations",
    "Human Resources",
    "Legal",
    "Healthcare",
    "Education",
    "Research",
] as const;

export const LEVEL_OPTIONS = [
    "Intern",
    "Staff",
    "Senior Staff",
    "Manager",
    "Senior Manager",
    "Director",
    "VP",
    "C-Suite",
] as const;

export type EducationOption = (typeof EDUCATION_OPTIONS)[number];
export type FunctionOption = (typeof FUNCTION_OPTIONS)[number];
export type LevelOption = (typeof LEVEL_OPTIONS)[number];
