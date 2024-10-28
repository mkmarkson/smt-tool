import pandas as pd
import streamlit as st


st.set_page_config(layout="wide")

def search_and_update(row, dataframe):
        service_name = row['Name']
    
        # Filter rows in dataframe where the service_name is in either the Summary or Description
        matches = dataframe[dataframe.apply(lambda x: service_name in str(x['Summary']) or service_name in str(x['Description']), axis=1)]
    
        # Count the number of matches
        match_count = len(matches)
    
        # Get the list of Issue Keys from the matches
        issue_keys = matches['Key'].tolist()
    
        # Return the match count and the issue keys
        return pd.Series([match_count, issue_keys])


# Function to find services mentioned in each row's Summary or Description
def find_services(row, services_list):
    # Extract the Summary and Description as strings
    summary = str(row['Summary'])
    description = str(row['Description'])
    
    # Check for each service if it's mentioned in either the Summary or Description
    mentioned_services = [service for service in services_list if service in summary or service in description]
    
    # Return the list of mentioned services
    return mentioned_services


def match_search(row, search_terms):
    summary = str(row['Summary']).lower() if pd.notna(row['Summary']) else ""
    description = str(row['Description']).lower() if pd.notna(row['Description']) else ""
    return any(term in summary or term in description for term in search_terms)


def recursive_boilerplate_generator(dataframe, key):
    key = key + 1  # Increment the key for Streamlit widget uniqueness
    block_col_temp1, block_col_temp2 = st.columns(2)  # Create two columns for input and output
    new_search_string = block_col_temp1.text_area("Text to filter out:", key=key)  # Search input

    # Ensure that search is not empty
    if new_search_string != "":
        # Process the input search string into a list of search terms
        new_search_terms = [term.strip().lower() for term in new_search_string.split(',')]
        
        # Filter the dataframe based on the match_search function
        internal_dataframe = dataframe[dataframe.apply(lambda row: match_search(row, new_search_terms), axis=1)].reset_index(drop=True)
        internal_dataframe_leftover = dataframe[~dataframe.apply(lambda row: match_search(row, new_search_terms), axis=1)].reset_index(drop=True)
        
        # Display the filtered dataframe in the second column
        block_col_temp2.dataframe(internal_dataframe, use_container_width=True)
        
        # Call the recursive function with the leftover dataframe
        if not internal_dataframe_leftover.empty:
            return recursive_boilerplate_generator(internal_dataframe_leftover, key)
        else:
            return internal_dataframe_leftover  # Return leftover if no more data remains
    else:
        return dataframe  # If no search input, return the original dataframe



uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None:

    requests_df = pd.read_csv(uploaded_file, dtype='unicode')

    requests_df['Summary'] = requests_df['Summary'].str.lower()
    requests_df['Description'] = requests_df['Description'].str.lower()
    requests_df = requests_df.rename(columns={'Issue key': 'Key'})

    services_df = pd.read_csv("managedServicesFullList.csv", dtype='unicode')
    services_df['Name'] = services_df['Name'].str.lower()

    block1_col1, block1_col2 = st.columns(2)

    block1_col1.title("Services")
    block1_col1.dataframe(services_df)
    block1_col2.title("Jira Issues")
    block1_col2.dataframe(requests_df)

    st.divider()

    individual_services_df = services_df

    individual_services_df['Count'] = 0
    individual_services_df['Linked Issue Keys'] = [[] for _ in range(len(individual_services_df))]

    individual_services_df[['Count', 'Linked Issue Keys']] = individual_services_df.apply(lambda row: search_and_update(row, requests_df), axis=1)

    # Sort the dataframe by the 'Count' column in descending order and reset the index
    individual_services_df = individual_services_df.sort_values(by='Count', ascending=False).reset_index(drop=True)

    block2_col1, block2_col2 = st.columns(2)

    block2_col1.title("Individual service name match:")

    block2_col1.dataframe(individual_services_df,use_container_width=True)

    block2_col2.title("Issues containing service names:")

    services_list = services_df['Name'].tolist()

    contained_services_df = requests_df
    contained_services_df['Contained Services'] = contained_services_df.apply(lambda row: find_services(row, services_list), axis=1)
    contained_services_df['Services Count'] = contained_services_df['Contained Services'].apply(len)

    block2_col2.dataframe(contained_services_df[['Summary', 'Description', 'Key', 'Contained Services', 'Services Count']].sort_values(by='Services Count', ascending=False).reset_index(drop=True))

    st.divider()

    tab_page1, tab_page2 = st.tabs(["Specific Services filter", "All Services filter"])

    with tab_page1: 

        page1_block1_col1, page1_block1_col2 = st.columns(2)

        min_value = contained_services_df["Services Count"].min()
        max_value = contained_services_df["Services Count"].max()

        st.subheader("Contained services count slider:")
        slider_value = st.slider("",label_visibility="hidden",min_value=min_value, max_value=max_value, value=1)
        
        filtered_contained_services_df = pd.DataFrame()

        filtered_contained_services_df = contained_services_df.loc[contained_services_df["Services Count"].eq(slider_value)].reset_index(drop=True)
        #filtered_dataframe = filtered_dataframe = df.loc[df["Services Count"].eq(slider_value)
        #                                ].reset_index(drop=True)
        
        filtered_issue_count = len(filtered_contained_services_df)
        
        page1_block1_col2.title("")
        page1_block1_col2.header(f"Filtered issue count: {filtered_issue_count}")
        page1_block1_col2.dataframe(filtered_contained_services_df)


        unique_services_df = filtered_contained_services_df.groupby(filtered_contained_services_df['Contained Services'].apply(tuple)).agg(
                Requests=('Contained Services', 'size'),  # Count occurrences of each unique list
                Keys=('Key', list)  # Aggregate corresponding Keys into a list
                ).reset_index().sort_values(by='Requests', ascending=False)

        unique_services_df['Contained Services'] = unique_services_df['Contained Services'].apply(list)

        unique_services_df_len = len(unique_services_df)
        page1_block1_col1.title("Services filter:")
        page1_block1_col1.header(f"Unique services count: {unique_services_df_len}")
        page1_block1_col1.dataframe(unique_services_df)
        total_sum = unique_services_df['Requests'].sum()
        page1_block1_col1.subheader(f"Sum of requests: {total_sum}")

        st.divider()

        page1_block2_col1, page1_block2_col2 = st.columns(2)
        services_options = unique_services_df['Contained Services'].tolist()

        options = page1_block2_col1.multiselect("Select Services:", services_options)

        # Step 1: Define a function to check if any option list is a subset of the 'Contained Services'
        def matches_any_option(services, options):
            return any(set(opt).issubset(set(services)) for opt in options)


        options_df = filtered_contained_services_df[filtered_contained_services_df['Contained Services'].apply(lambda services: matches_any_option(services, options))].reset_index(drop=True)

        page1_block2_col2.dataframe(options_df, use_container_width=True)

        st.divider()

        dup_option_df = options_df

        st.subheader("Filter by service:")
        st.dataframe(dup_option_df, use_container_width=True)

        key = 200
        
        if len(dup_option_df) != 0:
            # Call the recursive function with the initial dataframe and key
            dup_option_df_new_leftover2 = recursive_boilerplate_generator(dup_option_df, key)
        
            # Display the final leftover dataframe after recursion is complete
            st.subheader("Leftover:")
            st.dataframe(dup_option_df_new_leftover2, use_container_width=True)

    
    with tab_page2:

        page2_block1_col1, page1_block1_col2 = st.columns(2)

        services_options = services_df['Name'].tolist()

        tab_2options = page2_block1_col1.multiselect("Select Services:", services_options)
        print(tab_2options)

        pattern = '|'.join(tab_2options)
        tab_2filtered_df = requests_df[
                (requests_df['Summary'].str.contains(pattern, case=False, na=False)) |
                (requests_df['Description'].str.contains(pattern, case=False, na=False))
        ].reset_index(drop=True)

        page1_block1_col2.dataframe(tab_2filtered_df)

        st.divider()

        tab_2_dup_filtered_df = tab_2filtered_df

        st.subheader("Filter by service:")
        st.dataframe(tab_2_dup_filtered_df, use_container_width=True)

        tab2_key = 1
        
        if len(tab_2_dup_filtered_df) != 0:
            # Call the recursive function with the initial dataframe and key
            tab_2_dup_filtered_df2 = recursive_boilerplate_generator(tab_2_dup_filtered_df, tab2_key)
        
            # Display the final leftover dataframe after recursion is complete
            st.subheader("Leftover:")
            st.dataframe(tab_2_dup_filtered_df2, use_container_width=True)


    