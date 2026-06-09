export const INDIAN_CITIES: string[] = [
  "Mumbai", "Delhi", "Bangalore", "Bengaluru", "Hyderabad", "Ahmedabad",
  "Chennai", "Kolkata", "Pune", "Jaipur", "Lucknow", "Kanpur",
  "Nagpur", "Indore", "Thane", "Bhopal", "Visakhapatnam", "Patna",
  "Vadodara", "Ghaziabad", "Ludhiana", "Agra", "Nashik", "Faridabad",
  "Meerut", "Rajkot", "Varanasi", "Srinagar", "Aurangabad", "Dhanbad",
  "Amritsar", "Allahabad", "Ranchi", "Howrah", "Coimbatore", "Jabalpur",
  "Gwalior", "Vijayawada", "Jodhpur", "Madurai", "Raipur", "Kochi",
  "Chandigarh", "Mysore", "Guwahati", "Noida", "Gurgaon", "Dehradun",
  "Shimla", "Bhubaneswar", "Thiruvananthapuram", "Udaipur", "Surat",
  "Mangalore", "Tiruchirappalli", "Jalandhar", "Jamshedpur", "Aligarh"
]

export const CONTENT_TYPES: string[] = [
  "Influencer", "Actor", "Journalist", "Star", "Model", "Blogger",
  "Politician", "Activist", "Sportsperson", "Anchor", "Singer",
  "Dancer", "Entrepreneur", "Fashion Designer", "Chef", "Author",
  "Comedian", "Photographer", "Artist", "Doctor"
]

export const GENDER_OPTIONS = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "all", label: "All" },
] as const

export const SCHEDULE_OPTIONS = [
  { value: "manual", label: "Manual Only" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "every_6h", label: "Every 6 Hours" },
  { value: "custom", label: "Custom" },
] as const

export const DEFAULT_HASHTAGS: string[] = [
  "indianfemaleinfluencer", "indianmodel", "indianactress",
  "bollywood", "indianfashionblogger", "indianbeautyblogger"
]
